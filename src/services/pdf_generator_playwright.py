import os
import logging
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import asyncio
from src.models.report import Report, Plot

# Image handling
import aiohttp
import hashlib
import tempfile
import uuid
from io import BytesIO

try:
    from PIL import Image
except Exception:
    Image = None


from pypdf import PdfReader, PdfWriter

import shutil

logger = logging.getLogger(__name__)


class PDFGeneratorPlaywright:
    def __init__(self):
        repo_root = Path(__file__).resolve().parents[2]
        self.template_dir = repo_root / "template"
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        self.report_template = self.env.get_template("report_template.html")
        self.plot_template = self.env.get_template("plot_template.html")

    def _render_summary_html(self, report_data: Report) -> str:
        next_visit = getattr(report_data, "next_visit_date", None)
        current_visit = getattr(report_data, "current_visit_date", None)

        context = {
            "farm_name": report_data.farm_name,
            "consultant_name": report_data.consultant_name,
            "report_month": report_data.report_month,
            "owner_name": report_data.owner_name,
            "farm_city": report_data.farm_city,
            "harvest_period": report_data.harvest_period,
            "general_info": report_data.general_info,
            "next_visit_date": next_visit.strftime("%d/%m/%Y") if next_visit else "",
            "current_visit_date": current_visit.strftime("%d/%m/%Y")
            if current_visit
            else "",
            "operations_schedule": report_data.operations_schedule or "",
            "plots": [],  # Capa não mostra talhões
        }

        return self.report_template.render(**context)

    def _render_plot_html(self, plot: Plot) -> str:
        context = {"plot": plot}

        return self.plot_template.render(**context)

    async def _fetch_and_optimize_images(self, report_data: Report) -> dict:
        """Async download images referenced in report_data.plots and save optimized local files.

        Returns mapping {original_url: local_file_path, '_tmp_dir': tmp_dir}
        Implements concurrency, retries with exponential backoff, and a small disk cache.
        """
        mapping = {}
        tmp_dir = Path(tempfile.mkdtemp(prefix="pdf_images_"))

        # Conservative defaults to keep PDFs small
        max_width = 1200
        quality = 65
        concurrency = 6
        max_size_bytes = 10 * 1024 * 1024  # 10 MB
        max_retries = 3
        cache_dir = Path(self.template_dir.parent) / ".image_cache"
        try:
            cache_dir.mkdir(exist_ok=True)
        except Exception:
            pass

        async def _process_image_bytes(data: bytes, url: str, tmp_dir: Path) -> str:
            """Run Pillow processing in executor to avoid blocking the event loop."""

            def _sync_process():
                try:
                    if not Image:
                        suffix = url.split("?")[0].split(".")[-1].lower()
                        if suffix not in ("jpg", "jpeg", "png"):
                            suffix = "jpg"
                        fname = tmp_dir / f"{uuid.uuid4().hex}.{suffix}"
                        with open(fname, "wb") as f:
                            f.write(data)
                        return str(fname.resolve())

                    im = Image.open(BytesIO(data))
                    try:
                        exif = im._getexif()
                        if exif is not None:
                            orientation_key = 274
                            if orientation_key in exif:
                                orientation = exif[orientation_key]
                                if orientation == 3:
                                    im = im.rotate(180, expand=True)
                                elif orientation == 6:
                                    im = im.rotate(270, expand=True)
                                elif orientation == 8:
                                    im = im.rotate(90, expand=True)
                    except Exception:
                        pass
                    if im.mode in ("RGBA", "LA"):
                        bg = Image.new("RGB", im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[3])
                        im = bg
                    elif im.mode != "RGB":
                        im = im.convert("RGB")

                    if im.width > max_width:
                        new_h = int(im.height * (max_width / im.width))
                        im = im.resize((max_width, new_h), Image.LANCZOS)

                    fname = tmp_dir / f"{uuid.uuid4().hex}.jpg"
                    im.save(fname, format="JPEG", quality=quality)
                    return str(fname.resolve())
                except Exception:
                    suffix = url.split("?")[0].split(".")[-1].lower()
                    if suffix not in ("jpg", "jpeg", "png"):
                        suffix = "jpg"
                    fname = tmp_dir / f"{uuid.uuid4().hex}.{suffix}"
                    with open(fname, "wb") as f:
                        f.write(data)
                    return str(fname.resolve())

            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _sync_process)

        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(session: aiohttp.ClientSession, url: str):
            if url in mapping:
                return
            async with sem:
                # disk cache key
                key = hashlib.sha1(url.encode("utf-8")).hexdigest()
                cache_file = cache_dir / f"{key}.bin"
                cache_meta = cache_dir / f"{key}.meta"

                # attempt conditional headers
                headers = {}
                if cache_meta.exists():
                    try:
                        meta = cache_meta.read_text(encoding="utf-8")
                        for line in meta.splitlines():
                            if line.startswith("ETag:"):
                                headers["If-None-Match"] = line.split(":", 1)[1].strip()
                            if line.startswith("Last-Modified:"):
                                headers["If-Modified-Since"] = line.split(":", 1)[
                                    1
                                ].strip()
                    except Exception:
                        pass

                attempt = 0
                while attempt < max_retries:
                    try:
                        timeout = aiohttp.ClientTimeout(total=20)
                        async with session.get(
                            url, timeout=timeout, headers=headers
                        ) as resp:
                            if resp.status == 304 and cache_file.exists():
                                # not modified, reuse cache
                                local = str(cache_file.resolve())
                                mapping[url] = local
                                return
                            if resp.status != 200:
                                logger.warning(
                                    f"Image {url} returned status {resp.status}"
                                )
                                return
                            cl = resp.headers.get("Content-Length")
                            if cl and int(cl) > max_size_bytes:
                                logger.warning(
                                    f"Skipping {url}: Content-Length {cl} > {max_size_bytes}"
                                )
                                return
                            data = await resp.read()
                            if len(data) > max_size_bytes:
                                logger.warning(
                                    f"Skipping {url}: downloaded size {len(data)} > {max_size_bytes}"
                                )
                                return

                            # process and save optimized image
                            local = await _process_image_bytes(data, url, tmp_dir)

                            # update cache - best-effort
                            try:
                                with open(cache_file, "wb") as f:
                                    f.write(data)
                                meta_lines = []
                                etag = resp.headers.get("ETag")
                                if etag:
                                    meta_lines.append(f"ETag: {etag}")
                                lm = resp.headers.get("Last-Modified")
                                if lm:
                                    meta_lines.append(f"Last-Modified: {lm}")
                                if meta_lines:
                                    cache_meta.write_text(
                                        "\n".join(meta_lines), encoding="utf-8"
                                    )
                            except Exception:
                                pass

                            mapping[url] = local
                            return
                    except Exception:
                        attempt += 1
                        backoff = min(2**attempt + (0.1 * attempt), 10)
                        logger.exception(
                            f"Failed to download {url}, attempt {attempt}, retrying in {backoff}s"
                        )
                        await asyncio.sleep(backoff)
                logger.error(
                    f"Giving up downloading image after {max_retries} attempts: {url}"
                )

        # gather all distinct urls
        urls = []
        for p in report_data.plots or []:
            for img in getattr(p, "images", []) or []:
                url = None
                try:
                    url = img.url
                except Exception:
                    url = img.get("url") if isinstance(img, dict) else None
                if url:
                    urls.append(url)

        if not urls:
            mapping["_tmp_dir"] = str(tmp_dir)
            return mapping

        # prefer a session with limited per-host concurrency
        conn = aiohttp.TCPConnector(limit_per_host=concurrency)
        async with aiohttp.ClientSession(connector=conn) as session:
            tasks = [
                asyncio.create_task(_fetch_one(session, u)) for u in dict.fromkeys(urls)
            ]
            await asyncio.gather(*tasks)

        mapping["_tmp_dir"] = str(tmp_dir)
        return mapping

    def _generate_pdf_sync(self, html_content: str, pdf_path: str) -> str:
        """Synchronous generation using Playwright; writes PDF to path."""
        temp_name = f"temp_report_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.html"
        temp_path = self.template_dir / temp_name
        temp_path.write_text(html_content, encoding="utf-8")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(temp_path.as_uri(), wait_until="networkidle", timeout=30000)
                try:
                    imgs_state = page.evaluate(
                        "() => Array.from(document.images).map(i => ({src: i.src, naturalWidth: i.naturalWidth, complete: i.complete}))"
                    )
                    logger.debug(f"Document images state: {imgs_state}")
                except Exception:
                    logger.exception(
                        "Error evaluating document images state in Playwright page"
                    )
                page.emulate_media(media="screen")
                page.pdf(
                    path=pdf_path,
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "20mm",
                        "bottom": "20mm",
                        "left": "20mm",
                        "right": "20mm",
                    },
                )
                try:
                    browser.close()
                except Exception:
                    pass
        finally:
            try:
                temp_path.unlink()
            except Exception:
                pass

        return pdf_path

    async def _generate_pdfs_async(self, html_pdf_pairs: list) -> None:
        """Generate multiple PDFs reusing a single Playwright async browser instance.

        Recebe uma lista de (html_content, pdf_path) e gera cada PDF dentro do mesmo browser.
        """
        temp_files = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                for html_content, pdf_path in html_pdf_pairs:
                    temp_name = f"temp_report_{uuid.uuid4().hex}.html"
                    temp_path = self.template_dir / temp_name
                    temp_path.write_text(html_content, encoding="utf-8")
                    temp_files.append(temp_path)
                    page = await browser.new_page()
                    try:
                        await page.goto(
                            temp_path.as_uri(), wait_until="networkidle", timeout=30000
                        )
                        try:
                            await page.evaluate(
                                "() => Array.from(document.images).map(i => ({src: i.src, naturalWidth: i.naturalWidth, complete: i.complete}))"
                            )
                        except Exception:
                            logger.exception(
                                "Error evaluating document images state in Playwright page"
                            )
                        await page.emulate_media(media="screen")
                        await page.pdf(
                            path=pdf_path,
                            format="A4",
                            print_background=True,
                            margin={
                                "top": "20mm",
                                "bottom": "20mm",
                                "left": "20mm",
                                "right": "20mm",
                            },
                        )
                    finally:
                        try:
                            await page.close()
                        except Exception:
                            pass
                try:
                    await browser.close()
                except Exception:
                    pass
        finally:
            for tf in temp_files:
                try:
                    tf.unlink()
                except Exception:
                    pass

    async def generate_pdf(self, report_data: Report, output_path: str) -> str:
        """Main entry: fetch images, render small PDFs per section, merge into final PDF."""
        # fetch/optimize images (async implementation)
        mapping = await self._fetch_and_optimize_images(report_data)

        # ensure output dir
        os.makedirs(output_path, exist_ok=True)

        # create temporary dir for parts
        parts_dir = Path(tempfile.mkdtemp(prefix="pdf_parts_"))
        part_files = []

        try:
            # Prepare all HTML -> PDF pairs and render them in a single async browser session
            html_pdf_pairs = []
            # Capa/sumário: apenas informações gerais
            cover_html = self._render_summary_html(report_data)
            cover_pdf = str(parts_dir / f"part_cover_{uuid.uuid4().hex}.pdf")
            html_pdf_pairs.append((cover_html, cover_pdf))

            # Individual plots: um PDF para cada talhão
            for idx, plot in enumerate(report_data.plots or []):
                plot_html = self._render_plot_html(plot)
                for orig, local in list(mapping.items()):
                    if orig == "_tmp_dir":
                        continue
                    try:
                        plot_html = plot_html.replace(orig, Path(local).as_uri())
                    except Exception:
                        pass
                plot_pdf = str(parts_dir / f"part_plot_{idx}_{uuid.uuid4().hex}.pdf")
                html_pdf_pairs.append((plot_html, plot_pdf))

            # Render all PDFs reusando um único browser (async)
            await self._generate_pdfs_async(html_pdf_pairs)
            part_files.extend([p for _, p in html_pdf_pairs])

            # Merge parts using PdfReader/PdfWriter
            final_pdf = os.path.join(
                output_path, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            if PdfReader is None or PdfWriter is None:
                # if no merging library, fallback: if single part, move it; else raise
                if len(part_files) == 1:
                    shutil.move(part_files[0], final_pdf)
                else:
                    raise RuntimeError(
                        "pypdf/PyPDF2 not installed; cannot merge multiple PDF parts"
                    )
            else:
                writer = PdfWriter()
                for p in part_files:
                    try:
                        reader = PdfReader(p)
                        for page in reader.pages:
                            writer.add_page(page)
                    except Exception:
                        logger.exception(f"Failed to append part {p}")
                with open(final_pdf, "wb") as fout:
                    writer.write(fout)

            logger.info(f"PDF generated at {final_pdf}")
            return final_pdf
        finally:
            # cleanup
            try:
                tmpimg = mapping.get("_tmp_dir")
                if tmpimg:
                    shutil.rmtree(tmpimg, ignore_errors=True)
            except Exception:
                logger.exception("Failed to cleanup image tmp dir")
            try:
                shutil.rmtree(str(parts_dir), ignore_errors=True)
            except Exception:
                logger.exception("Failed to cleanup parts dir")

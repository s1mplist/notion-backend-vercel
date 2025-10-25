import logging
import os
import inspect
from notion_client import AsyncClient

from src.models import WebhookRequest
from src.services.notion_mapper import NotionDataMapper
from src.services.pdf_generator_playwright import PDFGeneratorPlaywright as PDFGenerator

from dotenv import load_dotenv

# Load env vars
load_dotenv("environments/prod/.env")

logger = logging.getLogger(__name__)


async def process_webhook_data(webhook_data: WebhookRequest) -> dict:
    """
    Process webhook data from Notion and generate PDF report.

    Args:
        webhook_data: Validated webhook data from Notion

    Returns:
        dict: Processing result with PDF generation status
    """
    try:
        logger.info(f"Processing webhook event: {webhook_data.type}")

        # Get data from Notion
        page_id = webhook_data.entity.get("id")
        if not isinstance(page_id, str) or not page_id:
            raise ValueError("Invalid or missing Notion page ID in webhook data.")
        notion_data = await get_notion_page(page_id)
        notion_id = notion_data.get("id")
        if not isinstance(notion_id, str) or not notion_id:
            raise ValueError("Invalid or missing Notion page ID in Notion data.")
        plots_data = await get_plots_data(notion_id)

        # Map data to report model
        mapper = NotionDataMapper()
        report_data = mapper.map_to_report(notion_data, plots_data)

        # Generate and save PDF
        pdf_generator = PDFGenerator()
        output_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(output_dir, exist_ok=True)

        # Support sync and async PDF generators (Playwright generator is async)
        maybe_coro = pdf_generator.generate_pdf(report_data, output_dir)
        if inspect.isawaitable(maybe_coro):
            pdf_path = await maybe_coro
        else:
            pdf_path = maybe_coro

        return {
            "status": "success",
            "message": "Report generated successfully",
            "pdf_path": pdf_path,
        }

    except Exception as e:
        logger.error(f"Error processing webhook data: {str(e)}", exc_info=True)
        raise


async def get_notion_page(page_id: str) -> dict:
    """
    Get page data from Notion API.

    Args:
        page_id: Notion page ID

    Returns:
        dict: Page data with properties
    """
    try:
        async with AsyncClient(auth=os.environ["NOTION_TOKEN"]) as notion:
            page = await notion.pages.retrieve(page_id=page_id)
            return page

    except Exception as e:
        logger.error(f"Error getting Notion page {page_id}: {str(e)}")
        raise


async def get_plots_data(report_id: str) -> list:
    """
    Get plots data from Notion database related to the report.

    Args:
        report_id: ID of the main report page

    Returns:
        list: List of plot pages data
    """
    try:
        logger.info(f"Retrieving plots for report ID: {report_id}")

        # Create a list to store the final plot data
        plots = []

        # Initialize the Notion client
        async with AsyncClient(auth=os.environ["NOTION_TOKEN"]) as notion:
            # Retrieve the page and get its properties
            page = await notion.pages.retrieve(page_id=report_id)
            properties = page["properties"]

            # Extract plot information from each talhao property
            for i in range(1, 19):  # Loop through all possible talhao entries (1-18)
                talhao_key = f"Talhão Visitado - {i:02d}"
                estagio_key = f"Estádio Fenológico - {i:02d}"
                avaliacao_key = f"Avaliação - {i:02d}"
                # fotos key names vary in casing/format; we'll normalize and search for them

                if talhao_key in properties:
                    talhao_data = properties[talhao_key].get("multi_select", [])
                    if talhao_data:  # If there's data for this talhao
                        # Try to find the fotos property in a case-insensitive way and support variations
                        found_key = None
                        # Use normalization utility to compare keys robustly
                        target1_norm = NotionDataMapper.normalize_prop_name(
                            f"Upload de fotos - {i:02d}"
                        )
                        target2_norm = NotionDataMapper.normalize_prop_name(
                            f"Upload de fotos - {i}"
                        )
                        for k in properties.keys():
                            kn = NotionDataMapper.normalize_prop_name(k)
                            if kn == target1_norm or kn == target2_norm:
                                found_key = k
                                break
                        # also support keys that start with the prefix (handles small variations)
                        if not found_key:
                            for k in properties.keys():
                                kn = NotionDataMapper.normalize_prop_name(k)
                                if kn.startswith(target1_norm) or kn.startswith(
                                    target2_norm
                                ):
                                    found_key = k
                                    break

                        fotos_prop = properties.get(found_key) if found_key else {}
                        # Log which key we used (or empty) for debugging when files are unexpectedly empty
                        logger.debug(
                            f"Fotos property for {talhao_key} (found key: {found_key}) -> {fotos_prop}"
                        )

                        files_list = []
                        if isinstance(fotos_prop, dict):
                            files_list = fotos_prop.get("files") or []

                        images = []
                        for file in files_list:
                            url = None
                            # Support both uploaded files and external links
                            if file.get("type") == "file":
                                url = file.get("file", {}).get("url")
                            elif file.get("type") == "external":
                                url = file.get("external", {}).get("url")
                            # Some SDK payloads may include the url at top-level keys
                            if not url:
                                url = file.get("url") or file.get("file_url")
                            if url:
                                images.append(
                                    {"url": url, "name": file.get("name", "")}
                                )

                        plot_data = {
                            "id": f"talhao_{i}",
                            "name": [t.get("name", "") for t in talhao_data],
                            "growth_stage": [
                                text.get("text", {}).get("content", "")
                                for text in properties.get(estagio_key, {}).get(
                                    "rich_text", []
                                )
                            ],
                            "assessment": [
                                text.get("text", {}).get("content", "")
                                for text in properties.get(avaliacao_key, {}).get(
                                    "rich_text", []
                                )
                            ],
                            "images": images,
                        }
                        plots.append(plot_data)

        logger.info(f"Plots data retrieved successfully for report ID: {report_id}")
        logger.debug(f"Plots data: {plots}")
        # If images are missing in the properties, try to find image blocks in the page body
        missing_images = any(len(p.get("images", [])) == 0 for p in plots)
        if missing_images:
            logger.info(
                "Some plots have no images in properties — scanning page blocks for image blocks as fallback"
            )
            try:
                # paginate through blocks
                blocks = []
                next_cursor = None
                while True:
                    resp = await notion.blocks.children.list(
                        block_id=report_id, start_cursor=next_cursor
                    )
                    blocks.extend(resp.get("results", []))
                    if not resp.get("has_more"):
                        break
                    next_cursor = resp.get("next_cursor")

                # Helper to get plain text from rich_text lists
                def rt_text(items):
                    if not items:
                        return ""
                    return " ".join(
                        it.get("text", {}).get("content", "") for it in items
                    )

                # Map of plot name tokens to index for simple matching
                name_index_map = {}
                for idx, p in enumerate(plots):
                    # use all name tokens lowercased
                    tokens = [
                        t.lower() for t in (p.get("name") or []) if isinstance(t, str)
                    ]
                    # also include id like 'talhao_1' and 'pivô 1' token variants
                    tokens.extend([p.get("id", "").lower()])
                    name_index_map[idx] = tokens

                unmatched = []
                # iterate blocks, try to match image blocks to plots
                for i, block in enumerate(blocks):
                    btype = block.get("type")
                    if btype != "image":
                        continue
                    image_obj = block.get("image", {})
                    # extract url
                    url = None
                    if image_obj.get("type") == "file":
                        url = image_obj.get("file", {}).get("url")
                    elif image_obj.get("type") == "external":
                        url = image_obj.get("external", {}).get("url")
                    if not url:
                        url = image_obj.get("url") or image_obj.get("file_url")

                    # caption text may help matching
                    caption = ""
                    try:
                        caption = rt_text(image_obj.get("caption", []))
                    except Exception:
                        caption = ""

                    matched = False
                    caption_l = caption.lower() if isinstance(caption, str) else ""

                    # look at nearby previous blocks' text (up to 3 previous)
                    nearby_text = caption_l
                    for j in range(max(0, i - 3), i):
                        blk = blocks[j]
                        t = ""
                        if blk.get("type") in (
                            "paragraph",
                            "heading_1",
                            "heading_2",
                            "heading_3",
                        ):
                            # paragraphs and headings have text in 'rich_text' or 'text'
                            rich = []
                            # different shapes possible
                            if blk.get(blk.get("type")):
                                rich = blk.get(blk.get("type")).get("rich_text", [])
                            if not rich and blk.get("paragraph"):
                                rich = blk.get("paragraph").get("rich_text", [])
                            t = rt_text(rich).lower()
                        nearby_text += " " + t

                    # try to match any plot by token presence
                    for idx, tokens in name_index_map.items():
                        for tok in tokens:
                            if not tok:
                                continue
                            if tok in nearby_text or tok in caption_l:
                                plots[idx].setdefault("images", []).append(
                                    {"url": url, "name": ""}
                                )
                                matched = True
                                break
                        if matched:
                            break

                    if not matched:
                        unmatched.append({"url": url, "caption": caption})

                # Assign unmatched images to plots that still have no images (left-to-right)
                uidx = 0
                for p in plots:
                    if len(p.get("images", [])) == 0 and uidx < len(unmatched):
                        p["images"] = [
                            {
                                "url": unmatched[uidx]["url"],
                                "name": unmatched[uidx].get("caption", ""),
                            }
                        ]
                        uidx += 1

                logger.debug(f"After block scan, plots data: {plots}")
            except Exception as e:
                logger.exception(f"Error scanning blocks for images: {e}")

        return plots

    except Exception as e:
        logger.error(f"Error getting plots data for report {report_id}: {str(e)}")
        raise e

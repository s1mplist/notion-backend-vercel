/**
 * Vercel Serverless Function - PDF Generation
 * CORRIGIDO: força retorno como Buffer
 */

const isProduction = process.env.VERCEL || process.env.NODE_ENV === 'production';

let chromium, puppeteer;

if (isProduction) {
  chromium = require('@sparticuz/chromium');
  puppeteer = require('puppeteer-core');
} else {
  puppeteer = require('puppeteer');
}

const MAX_TIMEOUT = 60000;
const https = require('https');
const sharp = require('sharp');

const keepAliveAgent = new https.Agent({ keepAlive: true, maxSockets: 50 });

function fetchWithTimeout(url, ms = 15000, init = {}) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), ms);

  const defaultHeaders = { 'User-Agent': 'Mozilla/5.0 (HeadlessChrome Puppeteer)' };
  const providedHeaders = (init && init.headers) || {};

  return fetch(url, {
    // Mantém querystring completa da URL pré-assinada
    signal: ac.signal,
    redirect: 'follow',
    // mescla headers (Content-Type / Cache-Control podem ser passados em init)
    headers: { ...defaultHeaders, ...providedHeaders },
    // Node fetch não aceita agent p/ https no global correto nas versões antigas do Node;
    // em Node 18+/22 funciona assim:
    agent: keepAliveAgent,
    // mantém outros init props (method, body, etc.)
    ...init,
  }).finally(() => clearTimeout(t));
}

async function inlineOptimizeImagesInHtml(html, baseURL, opts = {}) {
  // opts: { maxImageWidth, jpegQuality, maxDownloadBytes }
  const { maxImageWidth = 900, jpegQuality = 0.45, maxDownloadBytes = 10 * 1024 * 1024 } = opts;
  const imgRegex = /<img\b[^>]*\bsrc=(['"])(.*?)\1[^>]*>/gi;
  const processed = new Map();
  let match;
  // Collect unique srcs first to avoid re-fetching
  const srcs = [];
  while ((match = imgRegex.exec(html)) !== null) {
    const src = match[2];
    if (!src) continue;
    if (src.startsWith('data:')) continue;
    if (!processed.has(src)) {
      processed.set(src, null);
      srcs.push(src);
    }
  }

  for (const src of srcs) {
    let resolved;
    try {
      resolved = new URL(src, baseURL || undefined).href;
    } catch (e) {
      // cannot resolve URL, skip
      continue;
    }

    try {
      const resp = await fetchWithTimeout(resolved, 15000);
      if (!resp.ok) continue;
      const len = Number(resp.headers.get('content-length') || '0');
      if (len && len > maxDownloadBytes * 2) continue;
      const arrayBuf = await resp.arrayBuffer();
      const input = Buffer.from(arrayBuf);
      if (input.length > maxDownloadBytes * 2) continue;

      const img = sharp(input, { limitInputPixels: 268402689 }).rotate();
      const meta = await img.metadata().catch(() => ({}));
      const w = meta.width || 0;
      const h = meta.height || 0;

      const maxDim = Math.max(300, Number(maxImageWidth) || 900);
      const q = Math.max(30, Math.min(90, Math.round((Number(jpegQuality) || 0.45) * 100)));

      let pipeline = img;
      if (w && h && (w > maxDim || h > maxDim)) {
        pipeline = pipeline.resize({
          width: w >= h ? maxDim : undefined,
          height: h > w ? maxDim : undefined,
          fit: 'inside',
          withoutEnlargement: true,
          fastShrinkOnLoad: true,
        });
      }

      const out = await pipeline.jpeg({ quality: q, mozjpeg: true }).toBuffer();
      const dataUri = `data:image/jpeg;base64,${out.toString('base64')}`;
      processed.set(src, dataUri);
    } catch (e) {
      // ignore and leave original src
      processed.set(src, null);
    }
  }

  // Replace src attributes with data URIs where available
  let outHtml = html;
  for (const [orig, dataUri] of processed.entries()) {
    if (!dataUri) continue;
    // escape for regex
    const esc = orig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    outHtml = outHtml.replace(new RegExp(`(src=(\\"|\\')${esc}(\\"|\\'))`, 'g'), `src="${dataUri}"`);
  }

  return outHtml;
}

module.exports = async (req, res) => {
  // CORS básico
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(204).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({
      error: 'Method not allowed',
      message: 'Use POST method'
    });
  }

  const startTime = Date.now();
  let browser = null;

  try {
    const { html, options = {} } = req.body;

    if (!html || typeof html !== 'string') {
      return res.status(400).json({
        error: 'Invalid request',
        message: 'HTML content is required'
      });
    }

    const {
      format = 'A4',
      landscape = false,
      printBackground = true,
      preferCSSPageSize = true,
      margin = { top: '0', right: '0', bottom: '0', left: '0' },
      // Otimização para imagens remotas (inclui S3 pré-assinado)
      optimizeImages = true,
      maxImageWidth = 900,
      jpegQuality = 0.45,
      // Limites de proteção
      maxDownloadBytes = 10 * 1024 * 1024, // 10MB por imagem
      maxConcurrentImages = 6,
      baseURL,
    } = options;

    console.log('[PDF] Starting generation:', {
      environment: isProduction ? 'production' : 'development',
      htmlLength: html.length,
      options: { format, landscape, printBackground, preferCSSPageSize, optimizeImages, maxImageWidth, jpegQuality }
    });

    console.log('[PDF] Launching browser...');

    // Remote renderer fallback: if BROWSERLESS_URL or BROWSERLESS_TOKEN is set
    // use a managed rendering service (Browserless or self-hosted) to avoid
    // native library issues on Vercel (libnss3 and others).
    const browserlessUrl = process.env.BROWSERLESS_URL;
    const browserlessToken = process.env.BROWSERLESS_TOKEN;

    if (browserlessUrl || browserlessToken) {
      console.log('[PDF] Using remote renderer', { browserlessUrl: !!browserlessUrl, hasToken: !!browserlessToken });

      let endpoint;
      if (browserlessUrl) {
        endpoint = browserlessUrl;
      } else {
        // Default to browserless.io PDF endpoint when only token is provided
        endpoint = `https://production-sfo.browserless.io/pdf?token=${encodeURIComponent(browserlessToken)}`;
      }

      // Some browserless endpoints expect POST body with { html, options }
      // Browserless validation does NOT accept custom fields under options like `baseURL`.
      // Inject base URL into the HTML via a <base> tag instead of forwarding it in options.
      let htmlForRemote = html;
  if (baseURL && typeof baseURL === 'string') {
        try {
          const baseTag = `<base href="${baseURL}">`;
          if (/\<head[\s\S]*?\>/i.test(htmlForRemote)) {
            // insert right after opening <head>
            htmlForRemote = htmlForRemote.replace(/(\<head[\s\S]*?\>)/i, `$1${baseTag}`);
          } else if (/\<html[\s\S]*?\>/i.test(htmlForRemote)) {
            // insert a head section after opening <html>
            htmlForRemote = htmlForRemote.replace(/(\<html[\s\S]*?\>)/i, `$1<head>${baseTag}</head>`);
          } else {
            // fallback: prepend base tag
            htmlForRemote = `${baseTag}\n${htmlForRemote}`;
          }
        } catch (e) {
          console.warn('[PDF] Failed to inject base tag into HTML for remote renderer', e);
        }
      }

      // Inline & optimize remote images into the HTML so Browserless fetches don't
      // need to reach private/presigned URLs or be blocked; this keeps images in PDFs.
      if (optimizeImages) {
        try {
          htmlForRemote = await inlineOptimizeImagesInHtml(htmlForRemote, baseURL, { maxImageWidth, jpegQuality, maxDownloadBytes });
        } catch (e) {
          console.warn('[PDF] inlineOptimizeImagesInHtml failed, continuing without inlining', e);
        }
      }

      const payload = { html: htmlForRemote, options: { format, landscape, printBackground, preferCSSPageSize, margin } };

      console.log('[PDF] Sending HTML to remote renderer', { endpoint });
      const timeoutMs = Number(process.env.BROWSERLESS_TIMEOUT_MS || 30000);
      const remoteResp = await fetchWithTimeout(endpoint, timeoutMs, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' },
        body: JSON.stringify(payload),
      });

      if (!remoteResp.ok) {
        const txt = await remoteResp.text().catch(() => '');
        throw new Error(`Remote renderer failed: ${remoteResp.status} ${remoteResp.statusText} ${txt}`);
      }

      const arrayBuf = await remoteResp.arrayBuffer();
      const pdfBuffer = Buffer.from(arrayBuf);

      const duration = Date.now() - startTime;
      console.log('[PDF] Remote generation complete', { duration: `${duration}ms`, size: pdfBuffer.length });

      // Headers and return (same as local flow)
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Length', pdfBuffer.length.toString());
      res.setHeader('Content-Disposition', 'attachment; filename="relatorio.pdf"');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('X-Generation-Time', duration.toString());
      res.setHeader('X-PDF-Size', pdfBuffer.length.toString());
      res.setHeader('X-Environment', isProduction ? 'production' : 'development');

      return res.send(pdfBuffer);
    }

    if (isProduction) {
      browser = await puppeteer.launch({
        args: [
          ...chromium.args,
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--single-process',
          '--no-zygote',
        ],
        defaultViewport: chromium.defaultViewport,
        executablePath: await chromium.executablePath(),
        headless: chromium.headless,
      });
    } else {
      browser = await puppeteer.launch({
        headless: 'new',
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
        ],
      });
    }

    console.log('[PDF] Browser launched successfully');

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    await page.emulateMediaType('screen');

    if (optimizeImages) {
      const cache = new Map(); // url -> Buffer otimizada
      let inFlight = 0;
      const queue = [];

      await page.setRequestInterception(true);

      page.on('request', async (request) => {
        const type = request.resourceType();
        const url = request.url();

        // Só imagens reais via rede (S3, CDN). Ignora data: inline.
        if (type !== 'image' || url.startsWith('data:')) {
          return request.continue();
        }

        // Controle simples de concorrência
        const process = async () => {
          try {
            if (cache.has(url)) {
              const out = cache.get(url);
              return request.respond({ status: 200, contentType: 'image/jpeg', body: out });
            }

            const resp = await fetchWithTimeout(url, 15000);
            if (!resp.ok) {
              // Fallback: segue original
              return request.continue();
            }

            // Checar tamanho (Content-Length) para evitar baixar absurdos
            const len = Number(resp.headers.get('content-length') || '0');
            if (len && len > maxDownloadBytes * 2) {
              // Muito grande: não otimiza, segue original
              return request.continue();
            }

            // Baixar em Buffer com limite
            const arrayBuf = await resp.arrayBuffer();
            let input = Buffer.from(arrayBuf);
            if (input.length > maxDownloadBytes * 2) {
              // Proteção final
              return request.continue();
            }

            // Otimizar com sharp
            const img = sharp(input, { limitInputPixels: 268402689 }).rotate(); // protege ~16k x 16k
            const meta = await img.metadata().catch(() => ({}));
            const w = meta.width || 0;
            const h = meta.height || 0;

            const maxDim = Math.max(300, Number(maxImageWidth) || 900);
            const q = Math.max(30, Math.min(90, Math.round((Number(jpegQuality) || 0.45) * 100)));

            let pipeline = img;
            if (w && h && (w > maxDim || h > maxDim)) {
              pipeline = pipeline.resize({
                width: w >= h ? maxDim : undefined,
                height: h > w ? maxDim : undefined,
                fit: 'inside',
                withoutEnlargement: true,
                fastShrinkOnLoad: true,
              });
            }

            // Força JPEG para comprimir bem PNG/HEIC/WebP
            const out = await pipeline.jpeg({ quality: q, mozjpeg: true }).toBuffer();

            cache.set(url, out);
            return request.respond({ status: 200, contentType: 'image/jpeg', body: out });
          } catch (e) {
            try { request.continue(); } catch {}
          } finally {
            inFlight--;
            const next = queue.shift();
            if (next) next();
          }
        };

        if (inFlight >= maxConcurrentImages) {
          // fila
          queue.push(process);
        } else {
          inFlight++;
          process();
        }
      });
    }

    // Carregar conteúdo
    await page.setContent(html, {
      waitUntil: ['load', 'networkidle0'],
      timeout: MAX_TIMEOUT - 20000,
      ...(baseURL ? { baseURL } : {}),
    });

    // Ocultar/Remover barra de download se vier no HTML
    await page.addStyleTag({ content: '#report-download-bar{display:none!important;visibility:hidden!important}' });
    await page.evaluate(() => {
      const el = document.getElementById('report-download-bar');
      if (el) el.remove();
    });

    // Gerar PDF
    const pdfData = await page.pdf({
      format,
      landscape,
      printBackground,
      preferCSSPageSize,
      margin,
    });

    const pdfBuffer = Buffer.isBuffer(pdfData) ? pdfData : Buffer.from(pdfData);

    await browser.close();
    browser = null;

    const duration = Date.now() - startTime;
    console.log('[PDF] Generation complete:', {
      duration: `${duration}ms`,
      size: `${(pdfBuffer.length / 1024).toFixed(2)} KB (${(pdfBuffer.length / 1024 / 1024).toFixed(2)} MB)`,
      bufferLength: pdfBuffer.length,
      isBuffer: Buffer.isBuffer(pdfBuffer),
      dataConstructor: pdfData?.constructor?.name,
    });

    const header = pdfBuffer.slice(0, 8).toString('utf-8');
    if (!header.startsWith('%PDF-')) {
      throw new Error('Generated file is not a valid PDF');
    }

    // Headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Length', pdfBuffer.length.toString());
    res.setHeader('Content-Disposition', 'attachment; filename="relatorio.pdf"');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('X-Generation-Time', duration.toString());
    res.setHeader('X-PDF-Size', pdfBuffer.length.toString());
    res.setHeader('X-Environment', isProduction ? 'production' : 'development');

    return res.send(pdfBuffer);
  } catch (error) {
    console.error('[PDF] Error:', error);
    if (browser) { try { await browser.close(); } catch {} }
    const duration = Date.now() - startTime;
    return res.status(500).json({
      error: 'PDF generation failed',
      message: error.message,
      duration: `${duration}ms`,
      environment: isProduction ? 'production' : 'development',
    });
  }
};
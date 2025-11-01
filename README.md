# Notion Backend Vercel

API em FastAPI para integrar com o Notion, processar webhooks, consultar Data Sources (FACT e Talhões) e gerar relatórios HTML a partir de templates Jinja2. Pensado para rodar na Vercel (ASGI) e localmente para desenvolvimento.

## ✨ Principais recursos

- Recebe webhooks do Notion e processa em background
- Consulta Data Sources (FACT/Talhões) e combina os dados
- Gera HTML com templates modulares por fazenda/relatório
- Opcional: registra auditoria no Notion (metadados, links de preview/PDF)
- Utilidades para renderização, auditoria de HTML e organização de templates

## 📁 Estrutura (resumo)

    ```text
    src/
        main.py                 # App FastAPI e rotas
        api/
            health.py             # /health
            relatorios.py         # /report/{template}, /report/html-preview
            notion/webhook.py     # /notion/webhook
        core/config.py          # Configurações (Pydantic Settings)
        services/
            report/generator.py   # ReportGenerator (consulta + modelo + render)
            html/render.py        # HTMLRenderer (Jinja2 + assets inline)
            notion/
                notion_service.py   # NotionService (utilidades de Notion)
                writer.py           # NotionWriter (registros no Notion)
                mapper.py           # NotionDataMapper (mapeamento p/ modelo)
            data/plot_data.py     # PlotDataExtractor (imagens/avaliações)
            webhook/processor.py  # WebhookProcessor (pipeline de webhook)
        models/
            report.py, generation.py, webhook.py (ou equivalentes)
    templates/
        relatorios/
            terras-gerais/
                template.html, talhao.html, styles.css
    docs/                    # Documentação detalhada
    ```

## 🚀 Começando

Requisitos:

- Python 3.12+
- VS Code (recomendado)
- uv (ou pip)

Instalação de dependências:

    ```powershell
    uv sync
    # ou
    pip install -r requirements.txt
    ```

Variáveis de ambiente (crie `environments/.env`):

    ```text
    NOTION_TOKEN=...                      # obrigatório
    NOTION_FACT_DATABASE_ID=...           # obrigatório
    NOTION_TALHOES_DATABASE_ID=...        # obrigatório
    NOTION_OUTPUT_DATABASE_ID=...         # opcional (auditoria)
    PUBLIC_BASE_URL=https://seu-app.vercel.app  # opcional (links públicos)
    LOG_LEVEL=DEBUG
    ENABLE_HTML_AUDIT=false
    HTML_AUDIT_MAX_CHARS=12000
    ```

As variáveis são lidas por `core.config.Settings` (ver `src/core/config.py`).

### Rodando localmente

- Via task do VS Code: “Run FastAPI Server”
- Manualmente:

    ```powershell
    cd src
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

## 🔗 Endpoints

- GET `/` — status simples da API
- GET `/health` — health check detalhado
- POST `/notion/webhook` — recebe webhooks do Notion, processa em background
- GET `/report/{template}?page_id={FACT_PAGE_ID}` — renderiza HTML usando um template específico (bundle em `templates/relatorios/{template}`)
- GET `/report/html-preview?page_id={FACT_PAGE_ID}` — preview usando template padrão (compatibilidade)

Exemplo de chamada (PowerShell):

    ```powershell
    curl "http://localhost:8000/report/terras-gerais?page_id=SEU_PAGE_ID"
    ```

Observação: existe um endpoint experimental `GET /report/complete` em `src/main.py` para um fluxo alternativo; priorize `/report/{template}`.

## 🧩 Templates

Cada template é um bundle em `templates/relatorios/{slug}/`:

- `template.html` (principal)
- `styles.css` (estilos do bundle)
- Parciais como `talhao.html`

Renderize via: `GET /report/{slug}?page_id={FACT_PAGE_ID}`.

Renderização: `services.html.render.HTMLRenderer.render_template_slug`.

Mais detalhes: `docs/TEMPLATES.md`.

## 🕸️ Webhooks

- Rota: `POST /notion/webhook`
- Handler: `api/notion/webhook.py`
- Orquestração: `services/webhook/processor.py`
- Auditoria no Notion (opcional): `services/notion/writer.py`

Mais detalhes: `docs/WEBHOOKS.md`.

## 🛠️ Desenvolvimento

Lint e formatação (Ruff):

    ```powershell
    ruff check src/
    ruff format src/
    ```

Onde alterar o quê:

- Modelo de relatório: `models/report.py`
- Composição do modelo: `_build_report_model` em `services/report/generator.py`
- Consulta Notion/Data Sources: `services/notion/notion_service.py` e `services/report/generator.py`
- Renderização HTML: `services/html/render.py`

Mais detalhes: `docs/DEVELOPMENT.md` e `docs/FEATURES.md`.

## ✅ Testes

Quando houver testes em `tests/`:

    ```powershell
    python -m pytest tests/ -v
    ```

Mais detalhes: `docs/TESTING.md`.

## ☁️ Deploy (Vercel)

- Configure variáveis de ambiente no painel da Vercel
- O app ASGI é `src/main.py` (objeto `app`)
- Ajustes de rotas/tempo devem considerar execução serverless

Mais detalhes: `docs/OPERATIONS.md`.

## 📚 Documentação

- Onboarding: `docs/ONBOARDING.md`
- Arquitetura: `docs/ARCHITECTURE.md`
- Desenvolvimento: `docs/DEVELOPMENT.md`
- Templates: `docs/TEMPLATES.md`
- Operação: `docs/OPERATIONS.md`
- Webhooks: `docs/WEBHOOKS.md`
- Testes: `docs/TESTING.md`
- Novas features: `docs/FEATURES.md`

---

Se precisar, posso adicionar exemplos de payloads do Notion e coleções de requests (HTTP/Thunder Client) para acelerar testes locais.

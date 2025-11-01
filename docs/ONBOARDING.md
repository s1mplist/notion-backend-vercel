# Onboarding

Este guia ajuda você a subir o projeto em desenvolvimento, entender as rotas e verificar se tudo está funcionando.

## Pré‑requisitos

- Python 3.12+
- VS Code (recomendado)
- uv (gerenciador de dependências) ou pip
- Acesso a uma integração do Notion com permissões de leitura (e escrita para auditoria)

## 1) Configurar ambiente

- Copie `environments/.env.example` para `environments/.env` e preencha:
  - NOTION_TOKEN
  - NOTION_FACT_DATABASE_ID
  - NOTION_TALHOES_DATABASE_ID
  - (Opcional) NOTION_OUTPUT_DATABASE_ID
  - (Opcional) PUBLIC_BASE_URL
  - Ajuste LOG_LEVEL, ENABLE_HTML_AUDIT, HTML_AUDIT_MAX_CHARS se necessário
- As variáveis são carregadas por `core.config.Settings` (`src/core/config.py`).

## 2) Instalar dependências

- Via uv (recomendado):

```powershell
uv sync
```

- Via pip:

```powershell
pip install -r requirements.txt
```

## 3) Executar em desenvolvimento

- Task VS Code: “Run FastAPI Server”
  - Sobe em <http://localhost:8000>
- Manualmente:

```powershell
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 4) Rotas principais

As rotas são registradas em `src/main.py` e seus handlers estão em `src/api/`.

- Health: `GET /health` (handler em `api/health.py`)
- Preview HTML padrão: `GET /report/html-preview?page_id={FACT_PAGE_ID}` (reaproveita o template "terras-gerais")
- Render por template: `GET /report/{template}?page_id={FACT_PAGE_ID}` (handlers em `api/relatorios.py`)
- Webhook Notion: `POST /notion/webhook` (handler em `api/notion/webhook.py`)

Observação: existe um endpoint experimental `GET /report/complete` em `src/main.py` que depende de `ReportGenerator.generate_complete_report`. Use preferencialmente os endpoints de template.

## 5) Estrutura de templates

Cada template fica em `templates/relatorios/{slug}/` e normalmente contém:

- `template.html`
- `styles.css`
- parciais como `talhao.html`

A renderização é feita por `services.html.render.HTMLRenderer` (`src/services/html/render.py`).

## 6) Fluxo resumido de geração

- Consulta Data Sources (FACT/Talhões) via `services.report.generator.ReportGenerator`
- Constrói o modelo `models.report.Report`
- Renderiza HTML via Jinja2 (template bundle)
- (Opcional) Cria registro de auditoria no Notion via `services.notion.writer.NotionWriter`

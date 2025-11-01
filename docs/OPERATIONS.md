# Operação e Deploy

## Variáveis de ambiente

Definidas em `core.config.Settings` (`src/core/config.py`). Exemplos em `environments/.env.example`.

Principais:

- `NOTION_TOKEN`
- `NOTION_FACT_DATABASE_ID`, `NOTION_TALHOES_DATABASE_ID`
- `NOTION_OUTPUT_DATABASE_ID` (opcional)
- `PUBLIC_BASE_URL` (para links compartilháveis, se usado)
- `ENABLE_HTML_AUDIT`, `HTML_AUDIT_MAX_CHARS`
- `LOG_LEVEL`

## Logs e métricas

- Nível de log via `LOG_LEVEL`
- Auditoria de HTML: `HTMLRenderer` (`src/services/html/render.py`) com `enable_html_audit` e `html_audit_max_chars`
- Métricas: `enable_metrics`, `metrics_endpoint` em `core.config.Settings`

## Deploy (Vercel)

- Arquivo `vercel.json` já configurado
- Defina as variáveis de ambiente no painel da Vercel
- Entry point ASGI: `src/main.py` expõe `app`

## Rotina operacional

- Monitore falhas de integração com Notion (timeouts, HTTP 429, autenticação)
- Revise registros de auditoria (páginas criadas via `NotionWriter`)
- Atualize templates sem quebrar compatibilidade de dados (ver `docs/TEMPLATES.md`)

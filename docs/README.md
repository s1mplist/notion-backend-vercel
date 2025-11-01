# Notion Backend Vercel — Documentação

Este repositório contém uma API em FastAPI para:

- Receber webhooks do Notion, consolidar dados e registrar auditoria no Notion
- Consultar Data Sources do Notion (FACT e Talhões)
- Compor dados e renderizar relatórios HTML a partir de templates Jinja2
- (Opcional) Persistir metadados e enriquecer informações via outras fontes

Links úteis no código:

- Configuração: `core.config.Settings` em `src/core/config.py`
- Geração de relatórios: `services.report.generator.ReportGenerator` em `src/services/report/generator.py`
- Renderização HTML: `services.html.render.HTMLRenderer` em `src/services/html/render.py`
- Integração Notion: `services.notion.notion_service.NotionService` em `src/services/notion/notion_service.py`
- Escrita no Notion: `services.notion.writer.NotionWriter` em `src/services/notion/writer.py`
- Modelos: `models.report.Report` em `src/models/report.py`, `models.generation.GenerationMetadata` em `src/models/generation.py`
- Rotas FastAPI adicionadas em `src/main.py` e handlers em `src/api/`

Sumário desta documentação:

- Onboarding: `docs/ONBOARDING.md`
- Arquitetura: `docs/ARCHITECTURE.md`
- Desenvolvimento e Contribuição: `docs/DEVELOPMENT.md`
- Templates (criar/atualizar): `docs/TEMPLATES.md`
- Operação e Deploy: `docs/OPERATIONS.md`
- Webhooks e auditoria: `docs/WEBHOOKS.md`
- Testes: `docs/TESTING.md`
- Guia para Novas Features: `docs/FEATURES.md`

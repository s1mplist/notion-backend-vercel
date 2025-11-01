# Arquitetura

## Visão geral

- API FastAPI: `src/main.py` registra rotas; handlers em `src/api/`
  - `api/relatorios.py`: `report_by_template`, `report_html_preview`
  - `api/notion/webhook.py`: `webhook`
  - `api/health.py`: `health_check`
- Serviços:
  - Notion (leitura/escrita): `services.notion.notion_service.NotionService`, `services.notion.writer.NotionWriter`
  - Relatórios: `services.report.generator.ReportGenerator`
  - HTML: `services.html.render.HTMLRenderer`
  - Extração de plots/imagens: `services.data.plot_data.PlotDataExtractor`
  - Mapeamento de dados: `services.notion.mapper.NotionDataMapper`
  - Webhooks: `services.webhook.processor.WebhookProcessor`
- Modelos:
  - Relatório: `models.report.Report`
  - Metadados da geração: `models.generation.GenerationMetadata`
- Configuração: `core.config.Settings`

## Fluxo principal (report/template)

1. Endpoint: `api.relatorios.report_by_template` (rota `GET /report/{template}?page_id=...`)
2. Serviço: `services.report.generator.ReportGenerator`
   - `_get_data_sources`: resolve Data Sources (FACT, Talhões)
   - `_query_fact_data`: busca FACT pelo `page_id`
   - `_extract_farm_ids`: extrai `farm_ids`
   - `_query_talhoes_data`: busca Talhões por `farm_ids`
   - `_merge_plot_data`: mescla metadados de talhões com imagens/avaliações
   - `_build_report_model`: consolida em `models.report.Report`
3. Renderização: `services.html.render.HTMLRenderer.render_template_slug`
4. (Opcional) Auditoria/registro no Notion: `services.notion.writer.NotionWriter`

## Templates

- Localização: `templates/relatorios/{slug}/`
- Estrutura mínima:
  - `template.html` (pode incluir parciais, ex.: `talhao.html`)
  - `styles.css`
- Dados disponíveis: campos de `models.report.Report`

## Pontos de extensão

- Novas fontes de dados: criar serviço em `src/services/...` e integrar no `ReportGenerator`
- Novos campos no relatório: atualizar `models.report.Report`, ajustar `_build_report_model` e templates
- Novos templates: adicionar pasta em `templates/relatorios/{slug}` e usar `HTMLRenderer.render_template_slug`

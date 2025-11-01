# Webhooks, Geração e Auditoria

## Processamento

- Entrada: rota `POST /notion/webhook` adicionada em `src/main.py`
- Handler: `api.notion.webhook.webhook` (`src/api/notion/webhook.py`)
- Orquestração: `services.webhook.processor.WebhookProcessor` (`src/services/webhook/processor.py`)

Fluxo:

1. Recebe webhook e responde imediatamente (processamento em segundo plano)
2. Extrai `page_id` e carrega a página no Notion
3. Extrai dados de plots/imagens (`PlotDataExtractor`)
4. Resolve nome da fazenda (título do database)
5. Mapeia dados para `Report`
6. (Opcional) Enriquece com metadados adicionais
7. Gera metadados de geração e registra auditoria no Notion (se `NOTION_OUTPUT_DATABASE_ID` estiver configurado)

## Metadados da geração

- Modelo: `models.generation.GenerationMetadata` (`src/models/generation.py`)
  - Campos principais: `webhook_id`, `webhook_timestamp`, `entity_id`, `generation_started_at`, `generation_completed_at`, `generation_status`, `generation_error`

## Registro de auditoria/saída no Notion

- Escrita: `services.notion.writer.NotionWriter.create_generation_record`
  - Cria página no database `NOTION_OUTPUT_DATABASE_ID`
  - Adiciona payload do webhook (truncado), metadados e, quando aplicável, link de preview e PDF
  - Blocos montados por `_build_children_blocks`

## Respostas e links públicos

- Função de resposta de sucesso: `WebhookProcessor._build_success_response`
- `PUBLIC_BASE_URL` pode ser usado para montar `preview_url` público no retorno

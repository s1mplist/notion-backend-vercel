# Desenvolvimento e Contribuição

## Setup rápido

- Instale dependências com `uv sync` (ou `pip install -r requirements.txt`)
- Copie/edite `environments/.env`
- Use as tasks do VS Code (Run FastAPI Server, Ruff: Check Code, etc.)

## Padrões e qualidade

- Lint/format: Ruff
  - `ruff check src/`
  - `ruff format src/`
- Tipagem: `pyrightconfig.json` (opcional)

## Execução local

- API:

```powershell
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Rotas:
  - `GET /report/{template}?page_id=...`
  - `GET /report/html-preview?page_id=...`
  - `GET /health`
  - `POST /notion/webhook`

## Onde alterar o quê

- Adicionar campo novo no relatório:
  1) Modelo: `models.report.Report`
  2) Composição: `_build_report_model` em `services.report.generator.ReportGenerator`
  3) Template(s): `templates/relatorios/{slug}/template.html` (e parciais)
- Integrar nova propriedade do Notion:
  - Mapeamento/extração: `services.notion.mapper.NotionDataMapper`, `services.data.plot_data.PlotDataExtractor`
- Ajustar Data Sources:
  - Funções de leitura: `services.notion.notion_service.NotionService`
- Registrar auditoria no Notion:
  - Escrita: `services.notion.writer.NotionWriter`
  - Metadados: `models.generation.GenerationMetadata`

## Boas práticas

- Evite vazar dados sensíveis nos logs; use os utilitários de auditoria do `HTMLRenderer`
- Templates: otimize imagens e CSS para impressão/PDF (ver `docs/TEMPLATES.md`)
- Trate exceções de rede/Notion e mantenha logs contextuais

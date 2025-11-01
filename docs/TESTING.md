# Testes e Verificação

## Testes automatizados

- Estrutura padrão pytest (adicione a pasta `tests/` conforme for criando casos)
- Rodar (quando houver testes):

```powershell
python -m pytest tests/ -v
```

- Task VS Code: “Run Tests”

## Verificações estáticas

- Ruff:

```powershell
ruff check src/
ruff format src/
```

- (Opcional) Pre-commit:
  - Configure um `.pre-commit-config.yaml` com hooks (Ruff, etc.)
  - `pre-commit install`
  - `pre-commit run --all-files`

## Testes manuais de fluxo

- Preview HTML (template):
  - `GET /report/terras-gerais?page_id={FACT_PAGE_ID}`
  - `GET /report/html-preview?page_id={FACT_PAGE_ID}`
- Data Sources:
  - Verifique IDs em `environments/.env`
  - Funções de obtenção/consulta: `services.notion.notion_service.NotionService`

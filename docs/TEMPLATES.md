# Templates (criar e atualizar)

## Estrutura de um template

Caminho: `templates/relatorios/{slug}/`

- `template.html` (principal)
- `styles.css` (estilos do bundle)
- Parciais opcionais (ex.: `talhao.html`)

Exemplo existente:

- `terras-gerais/template.html`
- `terras-gerais/talhao.html`
- `terras-gerais/styles.css`

## Dados disponíveis no template

O contexto é preenchido a partir de `models.report.Report` em:

- `services.html.render.HTMLRenderer` (`src/services/html/render.py`)

Campos úteis em `template.html`:

- `farm_name`, `consultant_name`, `report_month`, `owner_name`, `farm_city`, `harvest_period`
- `general_info`, `operations_schedule`
- `current_visit_date`, `next_visit_date` (formatados como `dd/mm/yyyy`)
- `plots`: lista de `Plot` com imagens e avaliação

## Criar um novo template

1. Criar pasta `templates/relatorios/{meu-template}/`
2. Adicionar `template.html` (pode usar includes, ex.: `{% include 'talhao.html' %}`)
3. Adicionar `styles.css` com estilos de tela e impressão
4. (Opcional) Adicionar parciais, como `talhao.html`
5. Renderizar via rota:
   - `GET /report/{meu-template}?page_id={FACT_PAGE_ID}`
   - Internamente usa `ReportGenerator.generate_report_with_template`

## Boas práticas de CSS/HTML para PDF

- Use `@page` para tamanhos (A4/A3) e classes para controlar visualização vs impressão
- Evite quebrar componentes críticos: `break-inside: avoid;`
- Otimize imagens (dimensões, compressão); para preview use `loading="lazy"`
- Use parciais para manter o HTML modular e reutilizável

## Atualizar um template existente

- Edite `template.html` e/ou `styles.css`
- Valide em tela (preview) e como PDF
- Se adicionar novos campos, confira o contexto em `HTMLRenderer.render_template_slug` e ajuste `Report`/`_build_report_model` se necessário

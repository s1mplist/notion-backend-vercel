# Guia de Novas Features

## Checklist para novas features

1. Defina o objetivo e os dados necessários
2. Identifique onde buscar dados (Notion, APIs externas, etc.)
3. Atualize modelos, se necessário:
   - `models.report.Report` para campos de relatório
4. Mapeie/extraia dados:
   - Notion → `services.notion.mapper.NotionDataMapper`
   - Plots/Imagens → `services.data.plot_data.PlotDataExtractor`
5. Componha no relatório:
   - `_build_report_model` em `services.report.generator.ReportGenerator`
6. Renderize:
   - Atualize templates em `templates/relatorios/{slug}/`
7. Auditoria/registro (opcional):
   - `services.notion.writer.NotionWriter`

## Exemplos de extensão

- Novo campo `clima_resumo`:
  - Adicione em `models.report.Report`
  - Preencha na `_build_report_model(...)`
  - Exiba no(s) `template.html`

- Nova fonte (API externa):
  - Crie um serviço em `src/services/external/clima_service.py`
  - Chame-o no `ReportGenerator` antes da renderização
  - Passe o resultado para o modelo/template

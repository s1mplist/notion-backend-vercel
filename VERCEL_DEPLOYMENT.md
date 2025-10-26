# Vercel Deployment Guide

Este guia explica como fazer o deploy da aplicação Notion Backend no Vercel.

## 📁 Estrutura do Projeto

```
notion-backend-vercel/
├── api/
│   └── index.py          # Entry point para Vercel
├── src/                  # Código fonte principal
│   ├── main.py          # FastAPI app
│   ├── models/          # Modelos Pydantic
│   ├── services/        # Serviços de negócio
│   └── core/           # Configuração e infraestrutura
├── vercel.json          # Configuração do Vercel
└── pyproject.toml       # Dependências Python
```

## 🚀 Processo de Deploy

### 1. Pré-requisitos

- Conta no [Vercel](https://vercel.com)
- Projeto conectado ao GitHub
- Variáveis de ambiente configuradas

### 2. Variáveis de Ambiente

Configure as seguintes variáveis no dashboard do Vercel:

```bash
NOTION_API_TOKEN=secret_xxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  
VERCEL_BLOB_STORE_ID=your_store_id
VERCEL_BLOB_TOKEN=vercel_blob_xxxxxxxxxxxxx
```

### 3. Configuração do Build

O arquivo `vercel.json` já está configurado com:

- **Runtime**: Python 3.12
- **Handler**: `api/index.py`
- **Max Duration**: 30 segundos
- **Build Environment**: PYTHONPATH=./src

### 4. Entry Point (`api/index.py`)

O arquivo de entrada contém:

- **Mangum Adapter**: Converte FastAPI para ASGI compatível com Vercel
- **Path Management**: Adiciona `src/` ao Python path
- **Error Handling**: Captura e loga erros de execução
- **Logging**: Configuração otimizada para ambiente serverless

## 🔧 Recursos Implementados

### FastAPI Features
- ✅ Webhook endpoint (`/api/webhook`)
- ✅ Health check (`/health`)
- ✅ Validação de entrada com Pydantic
- ✅ Processamento assíncrono

### Infraestrutura
- ✅ Rate limiting
- ✅ Métricas e monitoramento
- ✅ Configuração centralizada
- ✅ Logging estruturado

### Integrações
- ✅ Notion API
- ✅ Vercel Blob Storage
- ✅ HTML/CSS templating

## 🧪 Testando o Deploy

### Localmente
```bash
# Instalar dependências
uv sync

# Testar importações
python check_deployment.py

# Executar testes
uv run --group tests pytest tests/ -v
```

### Endpoints Disponíveis

Após o deploy, os seguintes endpoints estarão disponíveis:

- `GET /` - Status da API
- `GET /health` - Health check detalhado
- `POST /api/webhook` - Webhook do Notion
- `GET /metrics` - Métricas da aplicação

## 🔍 Monitoramento

### Logs do Vercel
- Acesse o dashboard do Vercel
- Vá para "Functions" → "View Function Logs"
- Monitore erros e performance

### Métricas Customizadas
```bash
curl https://seu-app.vercel.app/metrics
```

## ⚡ Performance

### Otimizações Implementadas
- **Cold Start**: Mangum com `lifespan="off"`
- **Imports**: Lazy loading quando possível
- **Memory**: Configuração otimizada para serverless
- **Timeout**: 30s máximo por requisição

### Limites do Vercel
- **Memory**: 1024 MB (Hobby), 3000 MB (Pro)
- **Execution Time**: 10s (Hobby), 60s (Pro)
- **Bandwidth**: Unlimited

## 🛠️ Troubleshooting

### Erro de Import
```
ModuleNotFoundError: No module named 'src'
```
**Solução**: Verificar se `PYTHONPATH=./src` está no `vercel.json`

### Timeout de Função
```
Task timed out after 30.00 seconds
```
**Solução**: Otimizar processamento ou usar background tasks

### Erro de Dependência
```
No module named 'mangum'
```
**Solução**: Verificar se `mangum` está no `pyproject.toml`

## 📚 Recursos Adicionais

- [Vercel Python Guide](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/vercel/)
- [Mangum Documentation](https://mangum.fastapiexpert.com/)

## 🔄 CI/CD

O deploy acontece automaticamente quando:
1. Push para branch `main`
2. Pull request é mergeado
3. Tag é criada

Para deploys manuais:
```bash
vercel --prod
```
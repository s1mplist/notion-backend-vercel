# Logging no Vercel - Guia de Visualização

## Como visualizar os logs no dashboard do Vercel

### 1. Acesse o Dashboard do Vercel
- Vá para [vercel.com](https://vercel.com)
- Faça login na sua conta
- Selecione seu projeto `notion-backend-vercel`

### 2. Navegue até a aba "Functions"
- No menu lateral, clique em "Functions"
- Você verá uma lista das funções deployadas

### 3. Visualize os Logs
- Clique na função `src/main.py`
- Na página da função, clique na aba "Logs"
- Os logs aparecerão em tempo real

### 4. Filtros de Log
- Use os filtros para encontrar logs específicos:
  - **Level**: INFO, ERROR, WARNING, etc.
  - **Time Range**: Última hora, dia, semana
  - **Search**: Busque por termos específicos

## Tipos de Logs Configurados

### Logs de Request (Middleware)
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "event_type": "request_start",
  "request_method": "POST",
  "request_url": "https://your-app.vercel.app/api/webhook",
  "request_body_size": 1024,
  "request_headers": {...}
}
```

### Logs de Response
```json
{
  "timestamp": "2024-01-15T10:30:00.500Z",
  "level": "INFO", 
  "event_type": "request_end",
  "response_status": 200,
  "response_time_ms": 500.0
}
```

### Logs de Webhook
```json
{
  "timestamp": "2024-01-15T10:30:00.200Z",
  "level": "INFO",
  "event_type": "webhook_received",
  "webhook_payload_size": 1024,
  "webhook_content_type": "application/json",
  "webhook_user_agent": "Notion-Webhook/1.0",
  "webhook_payload_keys": ["type", "data", "timestamp"]
}
```

### Logs de Erro
```json
{
  "timestamp": "2024-01-15T10:30:00.300Z",
  "level": "ERROR",
  "event_type": "webhook_error",
  "error_type": "json_decode",
  "error_message": "Expecting ',' delimiter: line 1 column 10 (char 9)"
}
```

## Comandos Úteis para Debug

### Testar localmente
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar localmente
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Testar webhook
```bash
curl -X POST http://localhost:8000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "timestamp": "2024-01-15T10:30:00Z"}'
```

### Verificar logs em produção
```bash
# Usar Vercel CLI para ver logs em tempo real
vercel logs --follow
```

## Troubleshooting

### Se os logs não aparecem:
1. **Verifique se o deploy foi feito**: `vercel --prod`
2. **Confirme que está olhando a função correta**: `src/main.py`
3. **Teste com uma request**: Faça uma chamada para `/health` ou `/api/webhook`
4. **Verifique o nível de log**: Os logs estão configurados para nível INFO

### Logs muito verbosos:
- Para reduzir logs, altere o nível em `src/main.py`:
  ```python
  logger = setup_vercel_logging("WARNING")  # Apenas WARNING e ERROR
  ```

### Logs estruturados:
- Todos os logs são em formato JSON para facilitar análise
- Use os campos `event_type` para filtrar tipos específicos de eventos
- Os logs incluem timestamps precisos e informações de contexto

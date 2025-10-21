# Logging no Vercel - Guia de Visualização

## ⚠️ PROBLEMA RESOLVIDO: Logs não apareciam no Vercel

### ✅ Solução Implementada
- **Logging híbrido**: Usando tanto `print()` quanto `logger` para máxima compatibilidade
- **Emojis nos logs**: Para facilitar identificação visual
- **Logs estruturados**: Informações claras sobre requests e responses
- **Configuração simplificada**: Removida complexidade desnecessária

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
- Os logs aparecerão em tempo real com emojis para fácil identificação

### 4. Filtros de Log
- Use os filtros para encontrar logs específicos:
  - **Level**: INFO, ERROR, WARNING, etc.
  - **Time Range**: Última hora, dia, semana
  - **Search**: Busque por termos específicos como "🚀", "📨", "✅", "❌"

## Tipos de Logs Configurados

### 🚀 Logs de Request (Middleware)
```
🚀 REQUEST: POST https://your-app.vercel.app/api/webhook
✅ RESPONSE: 200 (45.23ms)
```

### 🏥 Logs de Health Check
```
🏥 HEALTH CHECK: Root endpoint accessed
🏥 HEALTH CHECK: Detailed health check requested
```

### 📨 Logs de Webhook
```
📨 WEBHOOK: Received 1024 bytes
📨 WEBHOOK: Payload keys: ['type', 'data', 'timestamp']
📨 WEBHOOK: Content-Type: application/json, User-Agent: Notion-Webhook/1.0
✅ WEBHOOK: Processed successfully, returning response
```

### ❌ Logs de Erro
```
❌ WEBHOOK: JSON decode error: Expecting ',' delimiter: line 1 column 10 (char 9)
❌ WEBHOOK: Processing error: Connection timeout
```

## Comandos Úteis para Debug

### Testar localmente
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar localmente
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Em outro terminal, executar o script de teste
python test_logs.py
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

# Ver logs de um deployment específico
vercel logs <deployment-url>
```

### Fazer deploy
```bash
# Deploy para produção
vercel --prod

# Verificar status do deploy
vercel ls
```

## Troubleshooting

### Se os logs ainda não aparecem:

1. **Verifique se o deploy foi feito**: `vercel --prod`
2. **Confirme que está olhando a função correta**: `src/main.py`
3. **Teste com uma request**: Faça uma chamada para `/health` ou `/api/webhook`
4. **Use o script de teste**: Execute `python test_logs.py`
5. **Verifique via CLI**: `vercel logs --follow`

### Logs muito verbosos:
- Para reduzir logs, altere o nível em `src/main.py`:
  ```python
  logging.basicConfig(level=logging.WARNING)  # Apenas WARNING e ERROR
  ```

### Logs estruturados:
- Todos os logs usam emojis para fácil identificação
- `print()` statements garantem compatibilidade com Vercel
- Logs incluem timestamps e informações de contexto
- Use os emojis para filtrar tipos específicos de eventos

## ✅ Checklist de Verificação

- [ ] Deploy feito com `vercel --prod`
- [ ] Teste local funcionando com `python test_logs.py`
- [ ] Logs aparecem no dashboard do Vercel
- [ ] Logs aparecem via `vercel logs --follow`
- [ ] Webhook recebendo requests corretamente

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.app:app",  # Caminho completo até o objeto 'app'
        port=8000,  # Porta padrão
        reload=True,  # Habilita recarregamento automático ao editar código
    )

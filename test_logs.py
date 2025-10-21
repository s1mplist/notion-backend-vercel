#!/usr/bin/env python3
"""
Script de teste para verificar se os logs estão funcionando no Vercel.
Execute este script para testar localmente antes de fazer deploy.
"""

import requests


def test_local_api():
    """Testa a API localmente"""
    base_url = "http://localhost:8000"

    print("🧪 Testando API localmente...")

    # Test 1: Health check
    print("\n1. Testando health check...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Erro: {e}")

    # Test 2: Root endpoint
    print("\n2. Testando root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Erro: {e}")

    # Test 3: Webhook endpoint
    print("\n3. Testando webhook endpoint...")
    test_payload = {
        "type": "test",
        "data": {"message": "Test webhook", "timestamp": "2024-01-15T10:30:00Z"},
    }

    try:
        response = requests.post(
            f"{base_url}/api/webhook",
            json=test_payload,
            headers={"Content-Type": "application/json"},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Erro: {e}")


def test_vercel_api(vercel_url):
    """Testa a API no Vercel"""
    print(f"\n🌐 Testando API no Vercel: {vercel_url}")

    # Test 1: Health check
    print("\n1. Testando health check no Vercel...")
    try:
        response = requests.get(f"{vercel_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Erro: {e}")

    # Test 2: Webhook endpoint
    print("\n2. Testando webhook no Vercel...")
    test_payload = {
        "type": "vercel_test",
        "data": {
            "message": "Test webhook from script",
            "timestamp": "2024-01-15T10:30:00Z",
            "source": "test_script",
        },
    }

    try:
        response = requests.post(
            f"{vercel_url}/api/webhook",
            json=test_payload,
            headers={"Content-Type": "application/json"},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Erro: {e}")


if __name__ == "__main__":
    print("🚀 Script de teste para logs do Vercel")
    print("=" * 50)

    # Teste local
    test_local_api()

    # Pergunta sobre URL do Vercel
    vercel_url = input(
        "\nDigite a URL do seu deploy no Vercel (ou Enter para pular): "
    ).strip()
    if vercel_url:
        test_vercel_api(vercel_url)

    print("\n✅ Teste concluído!")
    print("\n📋 Próximos passos:")
    print("1. Verifique os logs no dashboard do Vercel")
    print("2. Se não aparecer, execute: vercel logs --follow")
    print("3. Faça deploy: vercel --prod")

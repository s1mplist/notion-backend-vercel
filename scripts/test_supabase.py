"""
Exemplo de uso do Supabase Service.

Este script demonstra como usar o SupabaseService para:
- Criar e buscar fazendas
- Criar e buscar consultores
- Criar e buscar talhões
- Enriquecer relatórios com metadata
"""

import asyncio
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.supabase_service import supabase_service


async def exemplo_farms():
    """Exemplo de uso da tabela farms."""
    print("\n" + "=" * 60)
    print("📊 EXEMPLO: Gerenciamento de Fazendas")
    print("=" * 60)

    # Criar fazenda
    print("\n1️⃣ Criando nova fazenda...")
    farm = await supabase_service.create_farm(
        name="Fazenda Santa Maria",
        owner="Maria Santos",
        city="Ribeirão Preto",
        state="SP",
        total_area=250.5,
    )

    if farm:
        print(f"✅ Fazenda criada com ID: {farm['id']}")
        print(f"   Nome: {farm['name']}")
        print(f"   Proprietário: {farm['owner']}")
        print(f"   Localização: {farm['city']}/{farm['state']}")
    else:
        print("❌ Falha ao criar fazenda (pode já existir)")

    # Buscar fazenda
    print("\n2️⃣ Buscando fazenda por nome...")
    found_farm = await supabase_service.get_farm_by_name("Fazenda Santa Maria")

    if found_farm:
        print("✅ Fazenda encontrada:")
        print(f"   ID: {found_farm['id']}")
        print(f"   Proprietário: {found_farm['owner']}")
        print(f"   Área Total: {found_farm['total_area']} ha")
    else:
        print("❌ Fazenda não encontrada")

    # Listar todas
    print("\n3️⃣ Listando todas as fazendas...")
    all_farms = await supabase_service.list_farms()
    print(f"📋 Total de fazendas: {len(all_farms)}")
    for f in all_farms:
        print(f"   - {f['name']} ({f['city']}/{f['state']})")


async def exemplo_consultants():
    """Exemplo de uso da tabela consultants."""
    print("\n" + "=" * 60)
    print("👨‍🌾 EXEMPLO: Gerenciamento de Consultores")
    print("=" * 60)

    # Criar consultor
    print("\n1️⃣ Criando novo consultor...")
    consultant = await supabase_service.create_consultant(
        name="João Silva",
        email="joao.silva@email.com",
        phone="(16) 98765-4321",
        specialization="Nutrição de Plantas",
    )

    if consultant:
        print(f"✅ Consultor criado com ID: {consultant['id']}")
        print(f"   Nome: {consultant['name']}")
        print(f"   Email: {consultant['email']}")
        print(f"   Especialização: {consultant['specialization']}")
    else:
        print("❌ Falha ao criar consultor (pode já existir)")

    # Buscar consultor
    print("\n2️⃣ Buscando consultor por nome...")
    found_consultant = await supabase_service.get_consultant_by_name("João Silva")

    if found_consultant:
        print("✅ Consultor encontrado:")
        print(f"   Nome: {found_consultant['name']}")
        print(f"   Email: {found_consultant['email']}")
        print(f"   Telefone: {found_consultant['phone']}")
    else:
        print("❌ Consultor não encontrado")


async def exemplo_plots():
    """Exemplo de uso da tabela plots."""
    print("\n" + "=" * 60)
    print("🌱 EXEMPLO: Gerenciamento de Talhões")
    print("=" * 60)

    # Primeiro, buscar uma fazenda para vincular o talhão
    farm = await supabase_service.get_farm_by_name("Fazenda Santa Maria")

    if not farm:
        print("❌ Fazenda não encontrada. Crie uma fazenda primeiro.")
        return

    # Criar talhão
    print(f"\n1️⃣ Criando talhão na fazenda '{farm['name']}'...")
    plot = await supabase_service.create_plot(
        name="Talhão A1",
        farm_id=farm["id"],
        area=25.5,
        variety="Catuaí Vermelho",
        planting_date="2024-01-15",
    )

    if plot:
        print(f"✅ Talhão criado com ID: {plot['id']}")
        print(f"   Nome: {plot['name']}")
        print(f"   Área: {plot['area']} ha")
        print(f"   Variedade: {plot['variety']}")
    else:
        print("❌ Falha ao criar talhão (pode já existir)")

    # Buscar talhão
    print("\n2️⃣ Buscando talhão por nome...")
    found_plot = await supabase_service.get_plot_by_name(
        "Talhão A1", farm_id=farm["id"]
    )

    if found_plot:
        print("✅ Talhão encontrado:")
        print(f"   Nome: {found_plot['name']}")
        print(f"   Área: {found_plot['area']} ha")
        print(f"   Variedade: {found_plot['variety']}")
        print(f"   Data de Plantio: {found_plot['planting_date']}")
    else:
        print("❌ Talhão não encontrado")


async def exemplo_enrich_metadata():
    """Exemplo de enriquecimento de metadata."""
    print("\n" + "=" * 60)
    print("✨ EXEMPLO: Enriquecimento de Relatório")
    print("=" * 60)

    print(
        "\n🔍 Buscando metadata para 'Fazenda Santa Maria' e consultor 'João Silva'..."
    )

    metadata = await supabase_service.enrich_report_metadata(
        farm_name="Fazenda Santa Maria", consultant_name="João Silva"
    )

    if metadata:
        print("\n✅ Metadata enriquecida:")
        for key, value in metadata.items():
            print(f"   {key}: {value}")
    else:
        print("❌ Nenhuma metadata encontrada")


async def main():
    """Função principal de exemplo."""
    print("\n" + "=" * 80)
    print("🚀 EXEMPLOS DE USO DO SUPABASE SERVICE")
    print("=" * 80)

    # Verificar se Supabase está disponível
    if not supabase_service.is_available():
        print(
            "\n❌ Supabase não está configurado!\n"
            "\nPara usar este exemplo, configure as variáveis no .env:\n"
            "   SUPABASE_URL=https://seu-projeto.supabase.co\n"
            "   SUPABASE_KEY=sua-chave-aqui\n"
            "\nE instale a biblioteca:\n"
            "   uv add supabase\n"
        )
        return

    print(
        "\n✅ Supabase configurado e disponível!\n"
        "\nEste exemplo irá:\n"
        "   1. Criar e buscar fazendas\n"
        "   2. Criar e buscar consultores\n"
        "   3. Criar e buscar talhões\n"
        "   4. Demonstrar enriquecimento de metadata\n"
    )

    # Executar exemplos
    try:
        await exemplo_farms()
        await exemplo_consultants()
        await exemplo_plots()
        await exemplo_enrich_metadata()

        print("\n" + "=" * 80)
        print("✅ EXEMPLOS CONCLUÍDOS COM SUCESSO!")
        print("=" * 80)
        print(
            "\n💡 Dica: Acesse o Table Editor do Supabase para visualizar os dados criados."
        )

    except Exception as e:
        print(f"\n❌ Erro durante os exemplos: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

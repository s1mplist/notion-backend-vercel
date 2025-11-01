"""
Script para importar dados do Excel para o Supabase.

Importa dados de fazendas, consultores e talhões de um arquivo Excel
para as respectivas tabelas no Supabase.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
except ImportError:
    print("❌ pandas não está instalado. Instale com: pip install pandas openpyxl")
    sys.exit(1)

from src.services.supabase_service import supabase_service


async def import_farms(excel_path: str, sheet_name: str = "Fazendas") -> None:
    """
    Importa fazendas do Excel para o Supabase.

    Args:
        excel_path: Caminho para o arquivo Excel
        sheet_name: Nome da planilha (default: "Fazendas")
    """
    print(f"\n📊 Importando fazendas da planilha '{sheet_name}'...")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"❌ Erro ao ler planilha '{sheet_name}': {e}")
        return

    total = len(df)
    success = 0
    errors = 0

    for idx, row in df.iterrows():
        try:
            farm = await supabase_service.create_farm(
                name=row["Nome"],
                owner=row["Proprietário"],
                city=row.get("Cidade"),
                state=row.get("Estado"),
                total_area=row.get("Área Total"),
            )

            if farm:
                print(f"✓ [{idx + 1}/{total}] Fazenda '{row['Nome']}' importada")
                success += 1
            else:
                print(f"✗ [{idx + 1}/{total}] Falha ao importar '{row['Nome']}'")
                errors += 1

        except Exception as e:
            print(f"✗ [{idx + 1}/{total}] Erro ao importar '{row['Nome']}': {e}")
            errors += 1

    print(f"\n✅ Fazendas: {success} importadas, {errors} erros")


async def import_consultants(excel_path: str, sheet_name: str = "Consultores") -> None:
    """
    Importa consultores do Excel para o Supabase.

    Args:
        excel_path: Caminho para o arquivo Excel
        sheet_name: Nome da planilha (default: "Consultores")
    """
    print(f"\n📊 Importando consultores da planilha '{sheet_name}'...")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"❌ Erro ao ler planilha '{sheet_name}': {e}")
        return

    total = len(df)
    success = 0
    errors = 0

    for idx, row in df.iterrows():
        try:
            consultant = await supabase_service.create_consultant(
                name=row["Nome"],
                email=row.get("Email"),
                phone=row.get("Telefone"),
                specialization=row.get("Especialização"),
            )

            if consultant:
                print(f"✓ [{idx + 1}/{total}] Consultor '{row['Nome']}' importado")
                success += 1
            else:
                print(f"✗ [{idx + 1}/{total}] Falha ao importar '{row['Nome']}'")
                errors += 1

        except Exception as e:
            print(f"✗ [{idx + 1}/{total}] Erro ao importar '{row['Nome']}': {e}")
            errors += 1

    print(f"\n✅ Consultores: {success} importados, {errors} erros")


async def import_plots(excel_path: str, sheet_name: str = "Talhões") -> None:
    """
    Importa talhões do Excel para o Supabase.

    Requer que a planilha tenha uma coluna 'Fazenda' com o nome da fazenda
    para fazer o vínculo correto.

    Args:
        excel_path: Caminho para o arquivo Excel
        sheet_name: Nome da planilha (default: "Talhões")
    """
    print(f"\n📊 Importando talhões da planilha '{sheet_name}'...")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"❌ Erro ao ler planilha '{sheet_name}': {e}")
        return

    total = len(df)
    success = 0
    errors = 0

    for idx, row in df.iterrows():
        try:
            # Buscar fazenda pelo nome
            farm_name = row.get("Fazenda")
            if not farm_name:
                print(
                    f"✗ [{idx + 1}/{total}] Linha {idx + 1}: coluna 'Fazenda' não encontrada"
                )
                errors += 1
                continue

            farm = await supabase_service.get_farm_by_name(farm_name)
            if not farm:
                print(
                    f"✗ [{idx + 1}/{total}] Fazenda '{farm_name}' não encontrada no banco"
                )
                errors += 1
                continue

            # Criar talhão
            plot = await supabase_service.create_plot(
                name=row["Nome"],
                farm_id=farm["id"],
                area=row.get("Área"),
                variety=row.get("Variedade"),
                planting_date=row.get("Data de Plantio"),
            )

            if plot:
                print(
                    f"✓ [{idx + 1}/{total}] Talhão '{row['Nome']}' importado (Fazenda: {farm_name})"
                )
                success += 1
            else:
                print(f"✗ [{idx + 1}/{total}] Falha ao importar '{row['Nome']}'")
                errors += 1

        except Exception as e:
            print(f"✗ [{idx + 1}/{total}] Erro ao importar '{row['Nome']}': {e}")
            errors += 1

    print(f"\n✅ Talhões: {success} importados, {errors} erros")


async def main():
    """Função principal de importação."""
    print("=" * 60)
    print("🚀 IMPORTAÇÃO DE DADOS DO EXCEL PARA SUPABASE")
    print("=" * 60)

    # Verificar se Supabase está disponível
    if not supabase_service.is_available():
        print(
            "\n❌ Supabase não está configurado. Configure SUPABASE_URL e SUPABASE_KEY no .env"
        )
        return

    # Solicitar caminho do arquivo
    print("\n📁 Digite o caminho do arquivo Excel:")
    print("   Exemplo: C:\\Users\\Julia\\dados.xlsx")
    excel_path = input("   Caminho: ").strip()

    if not Path(excel_path).exists():
        print(f"\n❌ Arquivo não encontrado: {excel_path}")
        return

    # Confirmar importação
    print(f"\n⚠️  Você está prestes a importar dados de: {excel_path}")
    print("   Planilhas esperadas:")
    print("   - 'Fazendas' (colunas: Nome, Proprietário, Cidade, Estado, Área Total)")
    print("   - 'Consultores' (colunas: Nome, Email, Telefone, Especialização)")
    print("   - 'Talhões' (colunas: Nome, Fazenda, Área, Variedade, Data de Plantio)")
    confirm = input("\n   Continuar? (s/n): ").strip().lower()

    if confirm != "s":
        print("\n❌ Importação cancelada")
        return

    # Executar importações
    try:
        await import_farms(excel_path)
        await import_consultants(excel_path)
        await import_plots(excel_path)

        print("\n" + "=" * 60)
        print("✅ IMPORTAÇÃO CONCLUÍDA")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erro durante a importação: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

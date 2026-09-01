"""Verificação da instalação — diagnóstico passo a passo.

Confere, na ordem em que a implantação acontece, o que já está pronto e o
que falta, dizendo exatamente o que fazer em cada pendência.

    python verificar.py

Código de saída 0 quando o sistema está pronto para uso, 1 quando falta algo.
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "python"))

OK, FALHA, AVISO = "  [OK]   ", "  [FALTA]", "  [AVISO]"
_problemas: list[str] = []


def item(condicao: bool, titulo: str, detalhe: str = "",
         solucao: str = "", critico: bool = True) -> bool:
    if condicao:
        print(f"{OK} {titulo}" + (f" — {detalhe}" if detalhe else ""))
        return True
    marcador = FALHA if critico else AVISO
    print(f"{marcador} {titulo}" + (f" — {detalhe}" if detalhe else ""))
    if solucao:
        print(f"           → {solucao}")
    if critico:
        _problemas.append(titulo)
    return False


def secao(numero: str, texto: str) -> None:
    print(f"\n{numero}. {texto}")
    print("   " + "-" * 66)


def main() -> int:
    print("=" * 72)
    print("VERIFICAÇÃO DA INSTALAÇÃO — BANCO PRÓPRIO DE COMPOSIÇÕES")
    print("=" * 72)
    print(f"Pasta do sistema : {RAIZ}")
    portatil = (RAIZ / "python-portatil") in Path(sys.prefix).parents or \
               Path(sys.prefix).name == "python-portatil"
    print(f"Python           : {sys.version.split()[0]} ({platform.system()})"
          + ("  [portátil, incluso no pacote]" if portatil else ""))
    print(f"Interpretador    : {sys.executable}")

    # ------------------------------------------------------------ 1
    secao("1", "PYTHON E DEPENDÊNCIAS")
    item(sys.version_info >= (3, 10),
         "Python 3.10 ou superior",
         f"encontrado {sys.version_info.major}.{sys.version_info.minor}",
         "Instale o Python 3.10+ e recrie o ambiente virtual.")

    for modulo, para_que, obrigatorio in (
            ("openpyxl", "ler arquivos .xlsx", True),
            ("xlrd", "ler arquivos .xls (formato legado)", True),
            ("rapidfuzz", "similaridade textual", False)):
        try:
            __import__(modulo)
            item(True, f"Biblioteca {modulo}", para_que)
        except ImportError:
            item(False, f"Biblioteca {modulo}", para_que,
                 f"pip install -r requirements.txt", critico=obrigatorio)

    try:
        import sentence_transformers  # noqa: F401
        item(True, "sentence-transformers (opcional)", "embeddings neurais disponíveis")
    except ImportError:
        item(True, "sentence-transformers (opcional)",
             "ausente — o backend TF-IDF local será usado, sem prejuízo")

    if _problemas:
        print("\n" + "=" * 72)
        print("Resolva as dependências acima antes de continuar.")
        return 1

    from motor import config, database, ingest, loaders   # noqa: E402

    cfg = config.carregar(RAIZ)

    # ------------------------------------------------------------ 2
    secao("2", "PERMISSÃO DE GRAVAÇÃO NA PASTA")
    teste = RAIZ / "_permissao.tmp"
    try:
        teste.write_text("t", encoding="ascii")
        teste.unlink()
        gravavel = True
    except OSError:
        gravavel = False
    item(gravavel, "A pasta aceita gravação", str(RAIZ),
         "A raiz do disco (C:\\) e Arquivos de Programas exigem "
         "administrador. Mova a pasta inteira para Documentos ou para a "
         "Área de Trabalho e rode de lá.")

    secao("3", "BASES DE DADOS")
    # cfg.pasta_bases cai para a raiz quando BASES/ não existe. Aqui o teste
    # é explícito, senão o diagnóstico diria "OK" apontando para a raiz.
    pasta_bases = RAIZ / "BASES"
    if pasta_bases.is_dir():
        item(True, "Pasta BASES existe", str(pasta_bases))
        pasta = pasta_bases
    else:
        item(False, "Pasta BASES existe", "não encontrada",
             f"Crie a pasta: mkdir \"{pasta_bases}\" e copie os cinco "
             f"arquivos para dentro dela.")
        pasta = cfg.pasta_bases
        print(f"           procurando as bases em {pasta} (raiz do sistema)")

    planilhas = ([p for p in pasta.glob("*.xls*") if not p.name.startswith("~$")]
                 if pasta.is_dir() else [])
    item(len(planilhas) >= 5, "Cinco arquivos de base presentes",
         f"{len(planilhas)} encontrado(s)",
         "Veja BASES/LEIA-ME.txt para saber quais arquivos são esperados.")

    achados: dict[str, Path] = {}
    if planilhas:
        try:
            achados = ingest.descobrir_arquivos(cfg)
        except Exception as exc:                          # noqa: BLE001
            item(False, "Leitura das bases", str(exc)[:60])

    rotulos = {"SERVICOS": "Base de serviços da empresa",
               "MATERIAIS": "Base de materiais da empresa",
               "EDIF": "Composições EDIF",
               "INFRA": "Composições INFRA",
               "AUX": "Composições AUXILIARES"}
    for papel, rotulo in rotulos.items():
        caminho = achados.get(papel)
        item(caminho is not None, rotulo,
             caminho.name if caminho else "não identificada",
             "Confira BASES/LEIA-ME.txt; se preciso, indique o arquivo na "
             "aba CONFIGURAÇÃO (C13/C14/C15).")

    # Como cada base .xls foi identificada — prova de que não depende do nome.
    for papel in ("EDIF", "INFRA", "AUX"):
        caminho = achados.get(papel)
        if caminho is None:
            continue
        try:
            aba, linhas = loaders.ler_planilha(caminho)
            _, como = loaders.detectar_origem(aba, linhas, caminho.name)
            print(f"           {papel}: identificada por {como}")
        except Exception:                                 # noqa: BLE001
            pass

    # ------------------------------------------------------------ 3
    secao("4", "BANCO LOCAL")
    banco_existe = cfg.caminho_db.exists()
    item(banco_existe, "Banco banco_composicoes.db criado",
         cfg.caminho_db.name if banco_existe else "ainda não importado",
         'Rode: python python/main.py --json "{\\"acao\\":\\"atualizar_bases\\"}"')

    if banco_existe:
        con = database.conectar(cfg.caminho_db)
        try:
            contagens = {
                "Serviços da empresa": ("company_services", 1),
                "Materiais da empresa": ("company_materials", 1),
                "Composições de referência": ("reference_compositions", 1),
                "Insumos de referência": ("reference_inputs", 1),
            }
            for rotulo, (tabela, minimo) in contagens.items():
                total = database.escalar(con, f"SELECT COUNT(*) FROM {tabela}") or 0
                item(total >= minimo, rotulo, f"{total:,} registros".replace(",", "."),
                     'Rode: python python/main.py --json '
                     '"{\\"acao\\":\\"atualizar_bases\\"}"')

            for linha in con.execute(
                    "SELECT papel, nome_arquivo, data_base, data_importacao"
                    " FROM source_files ORDER BY papel"):
                print(f"           {linha['papel']:<10} {linha['nome_arquivo']:<32}"
                      f" {linha['data_base'] or '—':<10}"
                      f" importada em {linha['data_importacao'][:10]}")

            # Conhecimento já acumulado — não pode ser perdido em reimportações.
            secao("5", "CONHECIMENTO ACUMULADO (preservado entre atualizações)")
            for rotulo, sql in (
                    ("Vínculos de serviço confirmados",
                     "SELECT COUNT(*) FROM service_mappings"
                     " WHERE status='ATUAL' AND confirmado=1"),
                    ("Vínculos de material/equipamento",
                     "SELECT COUNT(*) FROM material_mappings"
                     " WHERE status='ATUAL' AND confirmado=1"),
                    ("Composições próprias",
                     "SELECT COUNT(*) FROM own_compositions"),
                    ("Regras de conversão cadastradas",
                     "SELECT COUNT(*) FROM conversion_rules"),
                    ("Pendências abertas",
                     "SELECT COUNT(*) FROM pending_mappings WHERE status='ABERTA'")):
                total = database.escalar(con, sql) or 0
                print(f"{OK} {rotulo} — {total}")
        finally:
            con.close()

    # ------------------------------------------------------------ 5
    secao("6", "MOTOR RESPONDENDO")
    try:
        from motor import api
        resposta = api.executar({"acao": "status", "raiz": str(RAIZ)})
        item(resposta.get("status") == "ok", "Motor responde à ação 'status'",
             resposta.get("backend_semantico", ""),
             resposta.get("erro", ""))
    except Exception as exc:                              # noqa: BLE001
        item(False, "Motor responde", str(exc)[:70])

    # ------------------------------------------------------------ 6
    secao("7", "INTERFACE EXCEL")
    xlsm = RAIZ / "Sistema_Composicoes.xlsm"
    xlsx = RAIZ / "Sistema_Composicoes.xlsx"
    modulos = sorted((RAIZ / "vba").glob("*.bas"))
    item(len(modulos) == 10, "Módulos VBA presentes",
         f"{len(modulos)} de 10", "Refaça o clone do repositório.")
    if xlsm.exists():
        item(True, "Sistema_Composicoes.xlsm pronto", "interface montada")
    elif xlsx.exists():
        item(False, "Sistema_Composicoes.xlsm", "existe apenas o .xlsx",
             "Rode: cscript //nologo instalar_vba.vbs   (ou importe os "
             "módulos manualmente — docs/INSTALACAO.md, seção 3b)",
             critico=False)
    else:
        item(False, "Pasta de trabalho do Excel", "não gerada",
             "Rode: python build_xlsm.py", critico=False)

    # ------------------------------------------------------------ resumo
    print("\n" + "=" * 72)
    if _problemas:
        print(f"FALTAM {len(_problemas)} ITEM(NS):")
        for p in _problemas:
            print(f"  - {p}")
        print("\nSiga as instruções marcadas com → acima.")
        return 1
    print("SISTEMA PRONTO PARA USO.")
    print("\nPróximos passos sugeridos:")
    print("  python prova_funcional.py       ver o fluxo completo em 6 serviços reais")
    print("  python -m pytest tests/ -q      rodar os 123 testes")
    if not xlsm.exists():
        print("  cscript //nologo instalar_vba.vbs   montar a interface do Excel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

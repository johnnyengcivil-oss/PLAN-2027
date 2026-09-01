"""Instala as bibliotecas a partir das rodas (.whl) que vêm no pacote.

Existe para o sistema não depender de internet na máquina de destino, nem
de o Python ter `pip` — o caso do Python portátil (embeddable), que vem
sem pip.

Duas estratégias, nessa ordem:

1. `pip install --no-index --find-links libs` quando há pip.
2. Extração direta das rodas em `site-packages`. Uma roda é um .zip com o
   pacote pronto; extrair equivale a instalar, para os pacotes que este
   sistema usa.

`rapidfuzz` é compilado, então depende da versão do Python. Se não houver
roda para a versão em uso, o sistema segue funcionando: `matching.py` cai
para `difflib` automaticamente.
"""
from __future__ import annotations

import shutil
import site
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PASTA_LIBS = RAIZ / "libs"

OBRIGATORIAS = {"openpyxl": "ler .xlsx", "xlrd": "ler .xls",
                "et_xmlfile": "dependência do openpyxl"}
OPCIONAIS = {"rapidfuzz": "similaridade textual (há alternativa embutida)"}


def destino_site_packages() -> Path:
    """Pasta onde os pacotes devem ficar para este interpretador."""
    for caminho in (sysconfig.get_paths().get("purelib"),
                    *(site.getsitepackages() if hasattr(site, "getsitepackages") else [])):
        if caminho:
            return Path(caminho)
    return Path(sys.prefix) / "Lib" / "site-packages"


def rodas_disponiveis() -> list[Path]:
    if not PASTA_LIBS.is_dir():
        return []
    return sorted(PASTA_LIBS.glob("*.whl"))


def roda_serve(roda: Path) -> bool:
    """Verifica se a roda é compatível com este Python.

    `nome-versao-pytag-abitag-plataforma.whl`. Rodas `py3-none-any`
    servem a qualquer versão; as compiladas exigem o cp da versão exata.
    """
    partes = roda.stem.split("-")
    if len(partes) < 3:
        return False
    pytag, plataforma = partes[2], partes[-1]
    if not pytag.startswith(("py2", "py3")):
        esperado = f"cp{sys.version_info.major}{sys.version_info.minor}"
        if pytag != esperado:
            return False
    if plataforma == "any":
        return True
    # Roda compilada: a plataforma também precisa bater.
    alvo = "win_amd64" if sys.platform == "win32" else sys.platform
    return plataforma.startswith(alvo)


def ja_instalado(pacote: str) -> bool:
    """Importa de verdade — instalado e importável não são a mesma coisa.

    Uma roda compilada para outra versão ou plataforma se instala mas
    falha ao importar, com AttributeError ou OSError em vez de
    ImportError. Por isso a captura é ampla.
    """
    try:
        __import__(pacote)
        return True
    except Exception:                            # noqa: BLE001
        return False


def tem_pip() -> bool:
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                       check=True, capture_output=True, timeout=90)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def instalar_com_pip(rodas: list[Path]) -> bool:
    comando = [sys.executable, "-m", "pip", "install",
               "--no-index", f"--find-links={PASTA_LIBS}",
               "--disable-pip-version-check", "--quiet"]
    comando += [r.name.split("-")[0].replace("_", "-") for r in rodas]
    try:
        subprocess.run(comando, check=True, timeout=600)
        return True
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"      pip não conseguiu instalar ({exc}); extraindo as rodas...")
        return False


def extrair_rodas(rodas: list[Path], destino: Path) -> None:
    """Extrai as rodas direto no site-packages, sem precisar de pip."""
    destino.mkdir(parents=True, exist_ok=True)
    for roda in rodas:
        nome = roda.name.split("-")[0]
        with zipfile.ZipFile(roda) as z:
            z.extractall(destino)
        print(f"      {nome} extraído")


def liberar_site_packages_do_portatil() -> None:
    """O Python portátil (embeddable) vem com `._pth` que desliga o
    site-packages. Sem esta correção, os pacotes instalados são ignorados."""
    for pth in Path(sys.prefix).glob("python*._pth"):
        texto = pth.read_text(encoding="utf-8")
        if "import site" in texto and not texto.count("#import site"):
            continue
        novo = texto.replace("#import site", "import site")
        if "Lib\\site-packages" not in novo:
            novo = novo.rstrip() + "\nLib\\site-packages\n"
        if novo != texto:
            pth.write_text(novo, encoding="utf-8")
            print(f"      {pth.name} ajustado para enxergar site-packages")


def main() -> int:
    print(f"      Python {sys.version.split()[0]} em {sys.prefix}")
    liberar_site_packages_do_portatil()

    faltando = [p for p in OBRIGATORIAS if not ja_instalado(p)]
    faltando += [p for p in OPCIONAIS if not ja_instalado(p)]
    if not faltando:
        print("      Todas as bibliotecas já estão disponíveis.")
        return 0

    rodas = [r for r in rodas_disponiveis() if roda_serve(r)]
    incompativeis = [r for r in rodas_disponiveis() if not roda_serve(r)]
    if incompativeis:
        nomes = {r.name.split("-")[0] for r in incompativeis}
        print(f"      (ignorando rodas de outra versão do Python: "
              f"{', '.join(sorted(nomes))})")

    if not rodas:
        print("      Nenhuma roda compatível em libs/. Tentando pela internet...")
        if tem_pip():
            subprocess.run([sys.executable, "-m", "pip", "install",
                            "-r", str(RAIZ / "requirements.txt")], check=False)
    else:
        if not (tem_pip() and instalar_com_pip(rodas)):
            extrair_rodas(rodas, destino_site_packages())

    # Confere o resultado de verdade, importando.
    problemas = []
    for pacote, para_que in OBRIGATORIAS.items():
        if ja_instalado(pacote):
            print(f"      [OK]    {pacote} — {para_que}")
        else:
            print(f"      [FALTA] {pacote} — {para_que}")
            problemas.append(pacote)
    for pacote, para_que in OPCIONAIS.items():
        estado = "OK   " if ja_instalado(pacote) else "ausente"
        print(f"      [{estado}] {pacote} — {para_que}")

    if problemas:
        print(f"\n      Não foi possível preparar: {', '.join(problemas)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Instala o `pmtiles` da versão fixada em carcara/config.py, conferindo o sha256 do arquivo baixado.

Uso, a partir da pasta do gerador:
    python scripts/install_pmtiles.py                 # em data/ferramentas/
    python scripts/install_pmtiles.py --dest /opt/pmtiles

Imprime o caminho do binário. Aponte CARCARA_PMTILES para ele (no GitHub Actions o script já deixa a variável
definida para os passos seguintes).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, pmtiles_tool  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala o pmtiles da versão fixada, com o sha256 conferido.")
    parser.add_argument("--dest", type=Path, default=config.DATA / "ferramentas", help="pasta de destino")
    args = parser.parse_args()
    binary = pmtiles_tool.install(args.dest)
    pmtiles_tool.require(str(binary))
    pmtiles_tool.export_to_actions(binary, os.environ.get("GITHUB_ENV"))
    print(f"[pmtiles] {config.PMTILES_VERSION} instalado em {binary}", file=sys.stderr)
    print(binary)
    return 0


if __name__ == "__main__":
    sys.exit(main())

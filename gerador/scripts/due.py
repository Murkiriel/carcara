"""Diz se está na hora de gerar de novo: a geração publicada completou o intervalo?

    python scripts/due.py                     # lê o catalogo.json da raiz; intervalo de 29 dias
    python scripts/due.py --interval-days 14
    python scripts/due.py --manual            # disparo à mão: sempre gera

Imprime o motivo e, no GitHub Actions, grava run=true ou run=false em $GITHUB_OUTPUT (o workflow gerar só segue
para a geração com run=true). Sem catálogo publicado, NÃO gera: a primeira geração é disparada à mão. Com um
catálogo que não dá para ler, não gera e termina com código 1, para o job ficar vermelho. A lógica fica em
carcara/schedule.py.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, schedule  # noqa: E402


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # acentos certos também com a saída redirecionada para arquivo
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--interval-days", type=int, default=config.GENERATION_INTERVAL_DAYS,
                        help="dias entre gerações (padrão: %(default)s)")
    parser.add_argument("--catalog", type=Path, default=config.REPO / "catalogo.json",
                        help="catálogo publicado (padrão: o da raiz do repositório)")
    parser.add_argument("--manual", action="store_true", help="disparo à mão: gera sem olhar a data")
    args = parser.parse_args()

    status, built_at = schedule.read_published(args.catalog)
    due, reason = schedule.generation_due(status, built_at, datetime.now(timezone.utc), args.interval_days,
                                          manual=args.manual)
    print(reason)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"run={'true' if due else 'false'}\n")
    return 0 if args.manual or schedule.is_readable(status, built_at) else 1


if __name__ == "__main__":
    sys.exit(main())

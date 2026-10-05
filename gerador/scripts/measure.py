"""Mede o tamanho que os recortes teriam, sem baixar nenhum tile (`pmtiles extract --dry-run`).

Uso, a partir da pasta do gerador:
    python scripts/measure.py                               # as 27 UFs, nos zooms 15 e 13
    python scripts/measure.py --areas DF,GO --zooms 15
    python scripts/measure.py --areas brasil --zooms 7,8,9,10

Cada simulação lê só os diretórios do build da Protomaps (poucos pedidos). O resultado vai para
data/medicoes/tamanhos_<build>.json, uma simulação por vez: se cair no meio, a próxima execução continua de onde
parou. Os tamanhos saem arredondados pela ferramenta; `archive_resolution` diz o quanto.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, extraction, regions, sources  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Simula os recortes e registra tiles e tamanho de cada um.")
    parser.add_argument("--areas", default=",".join(sorted(config.STATES)),
                        help="UFs separadas por vírgula, ou 'brasil' (padrão: as 27 UFs)")
    parser.add_argument("--zooms", default=f"{config.MAX_ZOOM},{config.LIGHT_MAX_ZOOM}",
                        help="zooms máximos a simular, separados por vírgula")
    parser.add_argument("--force", action="store_true", help="mede de novo o que já está no arquivo de resultados")
    args = parser.parse_args()
    areas = [a.strip() for a in args.areas.split(",") if a.strip()]
    zooms = [int(z) for z in args.zooms.split(",")]

    paths = regions.write_regions(sources.ibge_mesh(), config.REGIONS)
    unknown = [a for a in areas if a not in paths]
    if unknown:
        print(f"[medir] área desconhecida: {', '.join(unknown)}", file=sys.stderr)
        return 2
    build = sources.latest_build()
    print(f"[medir] build {build['key']} ({build['uploaded']}, esquema {build['version']}, "
          f"{build['size'] / 1e9:.1f} GB)")

    config.MEASUREMENTS.mkdir(parents=True, exist_ok=True)
    # Um arquivo por build: medir de novo com o build de outro dia não apaga as medições anteriores.
    results_path = config.MEASUREMENTS / f"tamanhos_{str(build['key']).removesuffix('.pmtiles')}.json"
    if results_path.exists():
        results = json.loads(results_path.read_text(encoding="utf-8"))
    else:
        results = {"build": build, "margin_deg": config.STATE_MARGIN_DEG, "estimates": {}}

    for area in areas:
        for zoom in zooms:
            key = f"{area}/{zoom}"
            if key in results["estimates"] and not args.force:
                continue
            start = time.monotonic()
            estimate = extraction.dry_run(str(build["url"]), paths[area], zoom)
            results["estimates"][key] = {
                "area": area, "maxzoom": zoom, "region_tiles": estimate.region_tiles,
                "tile_entries": estimate.tile_entries, "archive_bytes": estimate.archive_bytes,
                "archive_resolution": estimate.archive_resolution, "transfer_bytes": estimate.transfer_bytes,
                "requests": estimate.requests, "seconds": round(time.monotonic() - start, 1)}
            results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[medir] {area} até o zoom {zoom}: {estimate.region_tiles} tiles, "
                  f"{extraction.format_size(estimate.archive_bytes, estimate.archive_resolution)}, "
                  f"{estimate.requests} pedidos, {results['estimates'][key]['seconds']} s", flush=True)
    print(f"[medir] resultados em {results_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

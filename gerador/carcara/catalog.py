"""O catalogo.json: o índice que quem usa os pacotes lê para saber o que baixar, de onde e como conferir.

    {
      "schema": 1,
      "build_id": "2026-10-01-2b7e7669",     a geração; também o nome da release
      "built_at": "2026-10-01T17:30:00Z",
      "generator_commit": "abc1234",
      "tileset": {"name": "protomaps-basemap", "version": "4.15.2", "extensions": []},
      "source": {"kind": "protomaps-build", "timestamp", "url", "checksum", "osm_timestamp"},
      "tile_format": "mvt",
      "tile_compression": "gzip",
      "release_url": "https://github.com/<repositório>/releases/download/2026-10-01-2b7e7669/",
      "attribution": "...",
      "resources": {"file", "bytes", "sha256"},
      "base": {"file", "bytes", "sha256", "tiles", "minzoom", "maxzoom", "bbox", "bbox_tiles"},
      "states": {"GO": {"name": "Goiás", ...os mesmos campos, "light": {"file", "bytes", "sha256", "tiles",
                                                                        "minzoom", "maxzoom"}}, ...}
    }

`bbox` = [lat mín, lon mín, lat máx, lon máx] da área que o pacote atende (o polígono da UF no IBGE; na base, o
país), arredondado para fora. `bbox_tiles` = a área que os tiles do zoom mais fundo do pacote cobrem: é maior, porque
o recorte leva a margem e os tiles passam da divisa. O cabeçalho do PMTiles usa longitude primeiro; aqui é latitude
primeiro, como nos catálogos dos projetos irmãos.

`light` é opcional: uma geração sem pacotes leves não escreve a chave.
"""
from __future__ import annotations

import json
import math
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import config, mvt, packs, sources

SCHEMA = 1
TILESET_NAME = "protomaps-basemap"
SOURCE_KIND = "protomaps-build"
START_MARKER = "<!-- downloads:start -->"
END_MARKER = "<!-- downloads:end -->"

_FILE_KEYS = ("file", "bytes", "sha256", "tiles", "minzoom", "maxzoom")


def git_commit_hash() -> str:
    """Hash curto do commit do repositório, ou 'desconhecido' fora de um checkout do git."""
    try:
        done = subprocess.run(["git", "-C", str(config.REPO), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "desconhecido"
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else "desconhecido"


def polygon_bbox(bounds) -> List[float]:
    """[lat mín, lon mín, lat máx, lon máx] de um retângulo (oeste, sul, leste, norte), arredondado para fora em 2
    casas: nunca menor que a área."""
    west, south, east, north = bounds
    return [math.floor(south * 100) / 100, math.floor(west * 100) / 100,
            math.ceil(north * 100) / 100, math.ceil(east * 100) / 100]


def tiles_bbox(bounds, zoom: int) -> List[float]:
    """A área coberta pelos tiles do `zoom` que tocam o retângulo (oeste, sul, leste, norte), na mesma ordem do
    `bbox`, arredondada para fora em 4 casas."""
    west, south, east, north = bounds
    left, top = mvt.tile_at(north, west, zoom)
    right, bottom = mvt.tile_at(south, east, zoom)
    tile_west, _, _, tile_north = mvt.tile_bounds(zoom, left, top)
    _, tile_south, tile_east, _ = mvt.tile_bounds(zoom, right, bottom)
    return [math.floor(tile_south * 1e4) / 1e4, math.floor(tile_west * 1e4) / 1e4,
            math.ceil(tile_north * 1e4) / 1e4, math.ceil(tile_east * 1e4) / 1e4]


def _country_bounds(polygons: Dict[str, object]):
    boxes = [polygon.bounds for polygon in polygons.values()]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _entry(pack: dict, area_bounds) -> dict:
    entry = {key: pack[key] for key in _FILE_KEYS}
    entry["bbox"] = polygon_bbox(area_bounds)
    entry["bbox_tiles"] = tiles_bbox(pack["bounds"], int(pack["maxzoom"]))
    return entry


def build_catalog(build: Dict[str, object], generated: Dict[str, dict], resources_pack: Dict[str, object],
                  polygons: Dict[str, object], osm_timestamp: str, built_at: Optional[str] = None,
                  generator_commit: Optional[str] = None) -> dict:
    """O catálogo de uma geração: `generated` é o que o `packs.generate` devolve; `polygons`, a malha das UFs."""
    build_id = sources.build_id(build)
    states = {}
    for state in sorted(name for name in generated if name != packs.BASE):
        pack = generated[state]
        entry = {"name": config.STATES[state], **_entry(pack, polygons[state].bounds)}
        if pack.get("light"):
            entry["light"] = {key: pack["light"][key] for key in _FILE_KEYS}
        states[state] = entry
    return {
        "schema": SCHEMA,
        "build_id": build_id,
        "built_at": built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator_commit": generator_commit or git_commit_hash(),
        "tileset": {"name": TILESET_NAME, "version": str(build["version"]), "extensions": []},
        "source": {"kind": SOURCE_KIND, "timestamp": str(build["uploaded"]), "url": str(build["url"]),
                   "checksum": str(build["b3sum"]), "osm_timestamp": osm_timestamp},
        "tile_format": "mvt",
        "tile_compression": "gzip",
        "release_url": config.RELEASE_URL.format(tag=build_id),
        "attribution": config.ATTRIBUTION,
        "resources": {key: resources_pack[key] for key in ("file", "bytes", "sha256")},
        "base": _entry(generated[packs.BASE], _country_bounds(polygons)),
        "states": states,
    }


def save(catalog: dict, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _mb(size: int) -> str:
    return f"{size / 1e6:.1f}".replace(".", ",") + " MB"


def _link(catalog: dict, entry: Optional[dict]) -> str:
    """As duas células de um arquivo: o link para a release desta geração e o tamanho."""
    if not entry:
        return " | "
    return f"[{entry['file']}]({catalog['release_url']}{entry['file']}) | {_mb(entry['bytes'])}"


def downloads_table(catalog: dict) -> str:
    """A tabela de downloads do README: a base primeiro, depois as UFs pelo nome, com o completo e o leve de cada uma
    e o link direto para o arquivo na release desta geração."""
    source, resources_pack = catalog["source"], catalog["resources"]
    lines = [
        f"Geração **{catalog['build_id']}**: build da Protomaps de {source['timestamp'][:10]}, com dados do "
        f"OpenStreetMap de {source['osm_timestamp'][:10]}, no esquema {catalog['tileset']['version']}. Confira o "
        f"sha256 de cada arquivo pelo [`catalogo.json`](catalogo.json).",
        "",
        f"Ícones e fontes: [{resources_pack['file']}]({catalog['release_url']}{resources_pack['file']}) "
        f"({_mb(resources_pack['bytes'])}).",
        "",
        "| Pacote | Completo (até o zoom 15) | Tamanho | Leve (até o zoom 13) | Tamanho |",
        "|---|---|---:|---|---:|",
        f"| **Base** (o país até o zoom {catalog['base']['maxzoom']}) | {_link(catalog, catalog['base'])} | "
        f"{_link(catalog, None)} |",
    ]
    for state, entry in sorted(catalog["states"].items(), key=lambda item: _strip_accents(item[1]["name"])):
        lines.append(f"| {entry['name']} ({state}) | {_link(catalog, entry)} | {_link(catalog, entry.get('light'))} |")
    return "\n".join(lines)


def update_readme(text: str, table: str) -> str:
    """Troca só o que está entre os marcadores de downloads do README."""
    start, end = text.find(START_MARKER), text.find(END_MARKER)
    if start < 0 or end < start:
        raise ValueError(f"o README não tem os marcadores {START_MARKER} e {END_MARKER}")
    return text[:start + len(START_MARKER)] + "\n" + table + "\n" + text[end:]

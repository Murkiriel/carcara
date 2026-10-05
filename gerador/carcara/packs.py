"""Os pacotes de uma geração: um por estado, o leve de cada estado, e a base do país.

- O pacote do estado é recortado do build da Protomaps pelo polígono da UF com a margem, até o zoom 15.
- O pacote leve é recortado do pacote do estado já no disco, só até o zoom 13: não baixa nada a mais.
- A base é recortada do build pelo polígono do Brasil, até o zoom 9.

O que já foi feito fica anotado em `pacotes.json`, um pacote por vez: se a geração cair no meio, a execução seguinte
do mesmo build continua de onde parou. Com outro build, tudo começa de novo, e nada da geração anterior fica
misturado com a nova.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import config, extraction, regions
from .util import file_hash

BASE = "base"
BASE_FILE = "carcara-base.pmtiles"
MANIFEST = "pacotes.json"


def state_file(state: str) -> str:
    return f"carcara-{state}.pmtiles"


def light_file(state: str) -> str:
    return f"carcara-{state}-leve.pmtiles"


def _record(path: Path, summary: extraction.Estimate, maxzoom: int, seconds: float) -> Dict[str, object]:
    """Confere o arquivo recém-recortado e devolve o que se sabe dele."""
    extraction.verify(path)
    header = extraction.header(path)
    if (header.minzoom, header.maxzoom) != (0, maxzoom):
        raise RuntimeError(f"{path.name} saiu com os zooms {header.minzoom} a {header.maxzoom}; o pedido era 0 a "
                           f"{maxzoom}")
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": file_hash(path),
            "tiles": header.addressed_tiles, "tile_entries": header.tile_entries,
            "minzoom": header.minzoom, "maxzoom": header.maxzoom, "bounds": list(header.bounds),
            "transfer_bytes": summary.transfer_bytes, "requests": summary.requests, "seconds": round(seconds, 1)}


def _reusable(dist: Path, pack: Optional[Dict[str, object]]) -> bool:
    """O pacote anotado ainda está no disco, do mesmo tamanho?"""
    if not pack:
        return False
    path = dist / str(pack["file"])
    return path.is_file() and path.stat().st_size == pack["bytes"]


def _load_manifest(dist: Path, build: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    """Os pacotes já feitos deste build. Se o que há no disco é de outro build, apaga tudo e começa de novo."""
    path = dist / MANIFEST
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["build"]["key"] == build["key"] and manifest["build"]["b3sum"] == build["b3sum"]:
            return dict(manifest["packs"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    for old in [*dist.glob("carcara-*.pmtiles"), *dist.glob("carcara-*.pmtiles.parcial"), path]:
        old.unlink(missing_ok=True)
    return {}


def _save_manifest(dist: Path, build: Dict[str, object], done: Dict[str, Dict[str, object]]) -> None:
    text = json.dumps({"build": build, "packs": done}, ensure_ascii=False, indent=2) + "\n"
    (dist / MANIFEST).write_text(text, encoding="utf-8")


def _cut(source: str, dest: Path, maxzoom: int, region: Optional[Path]) -> Dict[str, object]:
    start = time.monotonic()
    summary = extraction.extract(source, dest, maxzoom, region)
    extraction.set_attribution(dest, config.EMBEDDED_ATTRIBUTION)  # antes de medir: o sha256 é o do arquivo final
    return _record(dest, summary, maxzoom, time.monotonic() - start)


def generate(build: Dict[str, object], region_paths: Dict[str, Path], states: List[str], dist: Path,
             light: bool = True) -> Dict[str, Dict[str, object]]:
    """Recorta os pacotes de `states` e a base. Devolve {UF ou "base": pacote}; o leve vai em `pacote["light"]`."""
    unknown = [state for state in states if state not in config.STATES]
    if unknown:
        raise ValueError(f"UF desconhecida: {', '.join(unknown)}")
    dist.mkdir(parents=True, exist_ok=True)
    done = _load_manifest(dist, build)
    url = str(build["url"])

    for name in [*states, BASE]:
        is_base = name == BASE
        pack = done.get(name)
        if not _reusable(dist, pack):
            file_name = BASE_FILE if is_base else state_file(name)
            maxzoom = config.BASE_MAX_ZOOM if is_base else config.MAX_ZOOM
            region = region_paths[regions.COUNTRY if is_base else name]
            print(f"[pacotes] {name}: recortando até o zoom {maxzoom}...", flush=True)
            pack = _cut(url, dist / file_name, maxzoom, region)
            pack["light"] = None
            print(f"[pacotes] {name}: {pack['tiles']} tiles, {pack['bytes'] / 1e6:.1f} MB em {pack['seconds']} s",
                  flush=True)
        else:
            print(f"[pacotes] {name}: já feito nesta geração", flush=True)
        if is_base or not light:
            if pack.get("light"):
                (dist / str(pack["light"]["file"])).unlink(missing_ok=True)
            pack["light"] = None
        elif not _reusable(dist, pack.get("light")):
            # Do arquivo completo que já está no disco: o leve não custa nenhum pedido ao build.
            pack["light"] = _cut(str(dist / str(pack["file"])), dist / light_file(name), config.LIGHT_MAX_ZOOM, None)
            pack["light"]["transfer_bytes"] = 0
            pack["light"]["requests"] = 0
            print(f"[pacotes] {name}: leve com {pack['light']['bytes'] / 1e6:.1f} MB", flush=True)
        done[name] = pack
        _save_manifest(dist, build, done)
    return {name: done[name] for name in [*states, BASE]}

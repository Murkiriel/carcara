"""As áreas de recorte: o polígono de cada UF com a margem, e o do Brasil para a base.

Cada área é gravada como um GeoJSON com a geometria solta (Polygon ou MultiPolygon, em longitude e latitude), que é o
que o `pmtiles extract --region` lê. O recorte pega os tiles que tocam a área.

A margem é a mesma dos tiles de roteamento, para a mesma conta escolher os pacotes dos dois projetos. Ilhas longe
do continente continuam partes separadas, e um estado com outro dentro continua com o buraco: o miolo do vizinho não
entra no pacote de quem está em volta.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from . import config

COUNTRY = "brasil"


def state_polygons(mesh: Path) -> Dict[str, object]:
    """{UF: geometria shapely} da malha do IBGE."""
    from shapely.geometry import shape

    gj = json.loads(mesh.read_text(encoding="utf-8"))
    polygons = {}
    for feature in gj["features"]:
        state = config.IBGE_STATE_CODES.get(str(feature["properties"]["codarea"]))
        if state is not None:
            polygons[state] = shape(feature["geometry"])
    return polygons


def with_margin(geometry, margin: float):
    """A geometria alargada em `margin` graus para todos os lados."""
    return geometry.buffer(margin)


def brazil(polygons: Dict[str, object], margin: float):
    """O país inteiro: a união das UFs, com a margem."""
    from shapely.ops import unary_union

    return with_margin(unary_union(list(polygons.values())), margin)


def write_regions(mesh: Path, folder: Path, margin: float = config.STATE_MARGIN_DEG) -> Dict[str, Path]:
    """Grava `<UF>.geojson` para as 27 UFs e `brasil.geojson` em `folder`. Devolve {nome: caminho}."""
    from shapely.geometry import mapping

    polygons = state_polygons(mesh)
    areas = {state: with_margin(geometry, margin) for state, geometry in polygons.items()}
    areas[COUNTRY] = brazil(polygons, margin)

    folder.mkdir(parents=True, exist_ok=True)
    for leftover in folder.glob("*.geojson"):
        leftover.unlink()  # sobra de outra malha ou de outra margem não pode ser recortada por engano
    paths = {}
    for name, area in areas.items():
        path = folder / f"{name}.geojson"
        path.write_text(json.dumps(mapping(area)), encoding="utf-8")
        paths[name] = path
    return paths

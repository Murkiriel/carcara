"""As travas antes de publicar: o que uma geração precisa ter para os pacotes poderem sair.

Cada trava devolve a lista dos problemas que achou, em frases. Uma geração só é publicável com a lista vazia.

- estrutura: o `pmtiles verify` aceita cada arquivo;
- cabeçalho: tiles vetoriais em gzip, do zoom 0 ao zoom do tipo de pacote, "clustered", e a área do arquivo cobre
  a UF (na base, todas as UFs);
- conteúdo: sobre a capital de cada UF, o tile do zoom mais fundo existe, decodifica e tem vias; o tile do zoom 12
  tem lugares;
- divisa: o tile sobre a divisa de cada par de UFs vizinhas é o mesmo, byte a byte, nos dois pacotes;
- tamanho: nenhum arquivo chega ao limite de um arquivo de release;
- queda: nenhum pacote perdeu mais que a tolerância de tiles ou de bytes em relação ao catálogo publicado;
- versão: os metadados de cada pacote trazem a versão do esquema do build desta geração;
- completude: cada UF pedida, a base e os recursos existem no disco, do tamanho anotado;
- recursos: o pacote de recursos tem toda fonte e todo ícone que os estilos de referência do esquema pedem.
"""
from __future__ import annotations

import io
import json
import struct
import tarfile
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from . import config, extraction, mvt, packs, resources

# Centro das capitais (nome, lat, lon). Um teste confere que cada ponto cai na UF pela malha do IBGE.
CAPITALS: Dict[str, Tuple[str, float, float]] = {
    "AC": ("Rio Branco", -9.9747, -67.8100), "AL": ("Maceió", -9.6658, -35.7353),
    "AM": ("Manaus", -3.1190, -60.0217), "AP": ("Macapá", 0.0349, -51.0694),
    "BA": ("Salvador", -12.9714, -38.5014), "CE": ("Fortaleza", -3.7319, -38.5267),
    "DF": ("Brasília", -15.7942, -47.8825), "ES": ("Vitória", -20.3155, -40.3128),
    "GO": ("Goiânia", -16.6869, -49.2648), "MA": ("São Luís", -2.5307, -44.3068),
    "MG": ("Belo Horizonte", -19.9167, -43.9345), "MS": ("Campo Grande", -20.4697, -54.6201),
    "MT": ("Cuiabá", -15.6014, -56.0979), "PA": ("Belém", -1.4558, -48.4902),
    "PB": ("João Pessoa", -7.1195, -34.8450), "PE": ("Recife", -8.0476, -34.8770),
    "PI": ("Teresina", -5.0920, -42.8038), "PR": ("Curitiba", -25.4284, -49.2733),
    "RJ": ("Rio de Janeiro", -22.9068, -43.1729), "RN": ("Natal", -5.7945, -35.2110),
    "RO": ("Porto Velho", -8.7612, -63.9004), "RR": ("Boa Vista", 2.8235, -60.6758),
    "RS": ("Porto Alegre", -30.0346, -51.2177), "SC": ("Florianópolis", -27.5954, -48.5480),
    "SE": ("Aracaju", -10.9472, -37.0731), "SP": ("São Paulo", -23.5505, -46.6333),
    "TO": ("Palmas", -10.2491, -48.3243),
}

# O zoom em que se confere que a cidade tem lugares (nomes): um tile de uns 10 km, que pega a capital e os bairros.
PLACES_ZOOM = 12
# Os zooms em que o tile de divisa é comparado entre vizinhos.
BORDER_ZOOMS = (config.MAX_ZOOM, 12)
# Folga, em graus, para dois polígonos da malha contarem como vizinhos (as divisas coincidem; isto cobre o arredondamento).
_TOUCH = 1e-4

# Os ícones que os estilos de referência do esquema pedem, lidos da fonte desses estilos (protomaps/basemaps,
# styles/src/base_layers.ts, revisão 42ffaaa de 2026-09-11): a seta de mão única, o ponto de cidade e de capital, e
# os escudos de rodovia por número de caracteres.
CORE_ICONS = ["arrow", "capital", "townspot"] + [f"{shield}-{chars}char" for shield in
                                                ("generic_shield", "US:I", "NL:S-road") for chars in range(1, 6)]
# E os dos pontos de interesse, que só as variações `light` e `dark` desenham. O estilo de referência pede também
# `townhall`, que a folha de ícones de origem não tem: é uma falha de lá, e fica de fora desta lista.
POI_ICONS = ["beach", "forest", "marina", "park", "peak", "zoo", "garden", "bench", "aerodrome", "train_station",
             "bus_stop", "ferry_terminal", "stadium", "university", "library", "school", "animal", "toilets",
             "drinking_water", "post_office", "building", "restaurant", "fast_food", "cafe", "bar", "supermarket",
             "convenience", "books", "beauty", "electronics", "clothes", "attraction", "museum", "theatre", "artwork"]
POI_FLAVORS = ("light", "dark")


def required_icons(flavor: str) -> List[str]:
    return CORE_ICONS + (POI_ICONS if flavor in POI_FLAVORS else [])


def _existing_files(dist: Path, generated: Dict[str, dict]) -> Iterator[Tuple[str, Path, int]]:
    """(UF ou "base", arquivo, zoom máximo esperado) de cada arquivo de tiles anotado que está no disco."""
    for name, pack in generated.items():
        full = dist / str(pack["file"])
        if full.is_file():
            yield name, full, config.BASE_MAX_ZOOM if name == packs.BASE else config.MAX_ZOOM
        light = pack.get("light")
        if light and (dist / str(light["file"])).is_file():
            yield name, dist / str(light["file"]), config.LIGHT_MAX_ZOOM


def check_structure(dist: Path, generated: Dict[str, dict]) -> List[str]:
    problems = []
    for _, path, _ in _existing_files(dist, generated):
        try:
            extraction.verify(path)
        except RuntimeError as e:
            problems.append(f"trava estrutura: {path.name}: {str(e).splitlines()[0]}")
    return problems


def _covers(bounds: Tuple[float, float, float, float], area: Tuple[float, float, float, float]) -> bool:
    west, south, east, north = bounds
    min_lon, min_lat, max_lon, max_lat = area
    slack = 1e-6
    return west <= min_lon + slack and south <= min_lat + slack and east >= max_lon - slack and north >= max_lat - slack


def _country_bounds(polygons: Dict[str, object]) -> Tuple[float, float, float, float]:
    boxes = [polygon.bounds for polygon in polygons.values()]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def check_headers(dist: Path, generated: Dict[str, dict], polygons: Dict[str, object]) -> List[str]:
    problems = []
    for name, path, maxzoom in _existing_files(dist, generated):
        try:
            header = extraction.header(path)
        except RuntimeError as e:
            problems.append(f"trava cabeçalho: {path.name}: {str(e).splitlines()[0]}")
            continue
        wrong = []
        if header.tile_type != "mvt":
            wrong.append(f"tiles do tipo {header.tile_type}, não mvt")
        if header.tile_compression != "gzip":
            wrong.append(f"compressão {header.tile_compression}, não gzip")
        if (header.minzoom, header.maxzoom) != (0, maxzoom):
            wrong.append(f"zooms {header.minzoom} a {header.maxzoom}, não 0 a {maxzoom}")
        if not header.clustered:
            wrong.append("não está clustered")
        area = _country_bounds(polygons) if name == packs.BASE else polygons[name].bounds
        if not _covers(header.bounds, area):
            wrong.append(f"a área do arquivo {list(header.bounds)} não cobre "
                         f"{'o país' if name == packs.BASE else name} {[round(v, 4) for v in area]}")
        if wrong:
            problems.append(f"trava cabeçalho: {path.name}: {'; '.join(wrong)}")
    return problems


def _layers_at(path: Path, lat: float, lon: float, zoom: int) -> Dict[str, int]:
    """As camadas do tile sobre o ponto. Lança ValueError com o motivo se o tile falta ou não decodifica."""
    x, y = mvt.tile_at(lat, lon, zoom)
    stored = extraction.read_tile(path, zoom, x, y)
    if stored is None:
        raise ValueError(f"falta o tile {zoom}/{x}/{y}")
    try:
        return mvt.read(stored)
    except ValueError as e:
        raise ValueError(f"o tile {zoom}/{x}/{y} não decodifica ({e})") from e


def _missing_layers(path: Path, lat: float, lon: float, zoom: int, layers: Tuple[str, ...]) -> Optional[str]:
    try:
        found = _layers_at(path, lat, lon, zoom)
    except (ValueError, RuntimeError) as e:
        return str(e)
    empty = [layer for layer in layers if not found.get(layer)]
    x, y = mvt.tile_at(lat, lon, zoom)
    return f"o tile {zoom}/{x}/{y} não tem feições em {', '.join(empty)}" if empty else None


def check_content(dist: Path, generated: Dict[str, dict]) -> List[str]:
    problems = []
    for name, path, maxzoom in _existing_files(dist, generated):
        capital, lat, lon = CAPITALS["DF" if name == packs.BASE else name]
        # No zoom mais fundo do pacote, as vias; no zoom da cidade, os lugares. A base só vai até um zoom de visão
        # geral, onde um tile só tem as duas coisas.
        wanted = [(maxzoom, ("roads", "places"))] if name == packs.BASE else [(maxzoom, ("roads",)),
                                                                              (PLACES_ZOOM, ("places",))]
        for zoom, layers in wanted:
            problem = _missing_layers(path, lat, lon, zoom, layers)
            if problem:
                problems.append(f"trava conteúdo: {path.name}, sobre {capital}: {problem}")
    return problems


def neighbours(polygons: Dict[str, object], states: List[str]) -> List[Tuple[str, str]]:
    """Os pares de UFs de `states` que fazem divisa, em ordem."""
    grown = {state: polygons[state].buffer(_TOUCH) for state in states if state in polygons}
    ordered = sorted(grown)
    return [(a, b) for i, a in enumerate(ordered) for b in ordered[i + 1:] if grown[a].intersects(grown[b])]


def border_point(a, b):
    """Um ponto sobre a divisa de duas UFs vizinhas."""
    return a.buffer(_TOUCH).intersection(b.buffer(_TOUCH)).representative_point()


def check_borders(dist: Path, generated: Dict[str, dict], polygons: Dict[str, object], states: List[str]) -> List[str]:
    problems = []
    for a, b in neighbours(polygons, [state for state in states if state in generated]):
        path_a, path_b = dist / str(generated[a]["file"]), dist / str(generated[b]["file"])
        if not (path_a.is_file() and path_b.is_file()):
            continue  # a completude já acusa o arquivo que falta
        point = border_point(polygons[a], polygons[b])
        for zoom in BORDER_ZOOMS:
            x, y = mvt.tile_at(point.y, point.x, zoom)
            try:
                tile_a, tile_b = extraction.read_tile(path_a, zoom, x, y), extraction.read_tile(path_b, zoom, x, y)
            except RuntimeError as e:
                problems.append(f"trava divisa: {a} e {b}, tile {zoom}/{x}/{y}: {str(e).splitlines()[0]}")
                continue
            missing = [path.name for path, tile in ((path_a, tile_a), (path_b, tile_b)) if tile is None]
            if missing:
                problems.append(f"trava divisa: {a} e {b}: o tile de divisa {zoom}/{x}/{y} falta em "
                                f"{' e '.join(missing)}")
            elif tile_a != tile_b:
                problems.append(f"trava divisa: {a} e {b}: o tile de divisa {zoom}/{x}/{y} é diferente nos dois "
                                f"pacotes ({len(tile_a)} e {len(tile_b)} bytes)")
    return problems


def _all_files(dist: Path, generated: Dict[str, dict], resources_pack: Optional[dict]) -> Iterator[Tuple[Path, dict]]:
    """(arquivo, anotação) de tudo o que a geração anotou, exista no disco ou não."""
    for pack in generated.values():
        yield dist / str(pack["file"]), pack
        if pack.get("light"):
            yield dist / str(pack["light"]["file"]), pack["light"]
    if resources_pack:
        yield dist / str(resources_pack["file"]), resources_pack


def check_sizes(dist: Path, generated: Dict[str, dict], resources_pack: Optional[dict]) -> List[str]:
    problems = []
    for path, _ in _all_files(dist, generated, resources_pack):
        if path.is_file() and path.stat().st_size >= config.MAX_ASSET_BYTES:
            problems.append(f"trava tamanho: {path.name} tem {path.stat().st_size / 1e9:.2f} GB; o limite por arquivo "
                            f"é {config.MAX_ASSET_BYTES / 1e9:.1f} GB")
    return problems


def _drop(label: str, new: dict, old: Optional[dict]) -> List[str]:
    found = []
    if not old:
        return found
    for key, unit in (("tiles", "tiles"), ("bytes", "bytes")):
        before, now = old.get(key), new.get(key)
        if isinstance(before, (int, float)) and before > 0 and now < before * (1 - config.MAX_DROP):
            found.append(f"{label} perdeu {100 * (before - now) / before:.1f}% dos {unit} em relação à geração "
                         f"publicada ({before} -> {now})")
    return found


def check_drop(generated: Dict[str, dict], published: Optional[dict], accept_drop: bool,
               log: Callable[[str], None]) -> List[str]:
    if not published:
        log("[validar] queda: primeira geração, não há catálogo publicado para comparar")
        return []
    drops = []
    for name, pack in generated.items():
        old = published.get("base") if name == packs.BASE else (published.get("states") or {}).get(name)
        drops += _drop(str(pack["file"]), pack, old)
        if pack.get("light"):
            drops += _drop(str(pack["light"]["file"]), pack["light"], (old or {}).get("light"))
    if drops and accept_drop:
        for drop in drops:
            log(f"[validar] queda aceita por --accept-drop: {drop}")
        return []
    return [f"trava queda: {drop} (tolerância de {100 * config.MAX_DROP:.0f}%; --accept-drop para publicar assim mesmo)"
            for drop in drops]


def check_version(dist: Path, generated: Dict[str, dict], build: dict) -> List[str]:
    problems = []
    expected = str(build["version"])
    for _, path, _ in _existing_files(dist, generated):
        try:
            version = str(extraction.metadata(path).get("version"))
        except RuntimeError as e:
            problems.append(f"trava versão: {path.name}: {str(e).splitlines()[0]}")
            continue
        if version.split(".")[0] != str(config.TILESET_MAJOR_VERSION):
            problems.append(f"trava versão: {path.name} é do esquema {version}; o gerador só aceita a versão maior "
                            f"{config.TILESET_MAJOR_VERSION}")
        elif version != expected:
            problems.append(f"trava versão: {path.name} é do esquema {version}, e o build desta geração é o "
                            f"{expected}: arquivo de outra geração")
    return problems


def check_completeness(dist: Path, generated: Dict[str, dict], resources_pack: Optional[dict], states: List[str],
                       light: bool) -> List[str]:
    problems = []
    for name in [*states, packs.BASE]:
        pack = generated.get(name)
        if not pack:
            problems.append(f"trava completude: falta o pacote de {name}")
        elif light and name != packs.BASE and not pack.get("light"):
            problems.append(f"trava completude: falta o pacote leve de {name}")
    if not resources_pack:
        problems.append("trava completude: falta o pacote de recursos")
    for path, record in _all_files(dist, generated, resources_pack):
        if not path.is_file():
            problems.append(f"trava completude: {path.name} não está no disco")
        elif path.stat().st_size != record["bytes"]:
            problems.append(f"trava completude: {path.name} tem {path.stat().st_size} bytes, e a anotação diz "
                            f"{record['bytes']}")
    return problems


def _png_size(data: bytes) -> Tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("não é um PNG")
    return struct.unpack(">II", data[16:24])


def _sprite_problems(files: Dict[str, bytes], flavor: str, density: str) -> List[str]:
    base = f"{resources.SPRITES_FOLDER}{flavor}{density}"
    try:
        index = json.loads(files[f"{base}.json"].decode("utf-8"))
        width, height = _png_size(files[f"{base}.png"])
        if not isinstance(index, dict):
            raise ValueError("o índice não é um objeto")
    except (ValueError, KeyError) as e:
        return [f"{base}.json e .png: não dá para ler ({e.__class__.__name__}: {e})"]
    found = []
    missing = [icon for icon in required_icons(flavor) if icon not in index]
    if missing:
        found.append(f"{base}.json: faltam os ícones {', '.join(missing[:8])}{'...' if len(missing) > 8 else ''}")
    outside = [name for name, icon in index.items()
               if not (isinstance(icon, dict) and 0 <= icon.get("x", -1) and 0 <= icon.get("y", -1)
                       and icon.get("x", 0) + icon.get("width", 0) <= width
                       and icon.get("y", 0) + icon.get("height", 0) <= height)]
    if outside:
        found.append(f"{base}: {len(outside)} ícones do índice ficam fora da imagem de {width}x{height}")
    return found


def check_resources(dist: Path, resources_pack: Optional[dict]) -> List[str]:
    if not resources_pack:
        return []  # a completude já acusa
    path = dist / str(resources_pack["file"])
    try:
        with tarfile.open(path, "r:gz") as tar:
            files = {member.name: tar.extractfile(member).read() for member in tar if member.isfile()}
    except (tarfile.TarError, OSError, EOFError) as e:
        return [f"trava recursos: {path.name} não abre ({e.__class__.__name__}: {e})"]
    found = []
    missing = [name for name in [*resources.required(), resources.ICONS_LICENCE, resources.README] if name not in files]
    if missing:
        found.append(f"faltam {len(missing)} arquivos: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
    for flavor in resources.SPRITE_FLAVORS:
        for density in ("", "@2x"):
            if f"{resources.SPRITES_FOLDER}{flavor}{density}.json" in files \
                    and f"{resources.SPRITES_FOLDER}{flavor}{density}.png" in files:
                found += _sprite_problems(files, flavor, density)
    return [f"trava recursos: {path.name}: {problem}" for problem in found]


def validate(dist: Path, generated: Dict[str, dict], resources_pack: Optional[dict], build: dict,
             polygons: Dict[str, object], states: List[str], light: bool, published: Optional[dict] = None,
             accept_drop: bool = False, log: Callable[[str], None] = print) -> List[str]:
    """Roda todas as travas sobre a geração em `dist`. Devolve os problemas; lista vazia = publicável."""
    checks = [
        ("estrutura", lambda: check_structure(dist, generated)),
        ("cabeçalho", lambda: check_headers(dist, generated, polygons)),
        ("conteúdo", lambda: check_content(dist, generated)),
        ("divisa", lambda: check_borders(dist, generated, polygons, states)),
        ("tamanho", lambda: check_sizes(dist, generated, resources_pack)),
        ("queda", lambda: check_drop(generated, published, accept_drop, log)),
        ("versão", lambda: check_version(dist, generated, build)),
        ("completude", lambda: check_completeness(dist, generated, resources_pack, states, light)),
        ("recursos", lambda: check_resources(dist, resources_pack)),
    ]
    problems: List[str] = []
    for name, check in checks:
        found = check()
        log(f"[validar] {name}: {'ok' if not found else str(len(found)) + ' problema(s)'}")
        problems += found
    return problems

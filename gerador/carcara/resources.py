"""O pacote de recursos: as fontes dos rótulos e as folhas de ícones que os estilos do esquema pedem.

Vêm do repositório de recursos do basemap da Protomaps, numa revisão fixa (config.ASSETS_REVISION). Do que há lá,
entram as fontes em PBF por faixa (`fonts/<fonte>/<faixa>.pbf`) e as folhas de ícones da versão 4 do esquema
(`sprites/v4/`), nos caminhos que o MapLibre procura. O resto (scripts, folhas de versões antigas) fica de fora.

O arquivo de saída é reproduzível: a mesma revisão dá sempre o mesmo `.tar.gz`, byte a byte.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
from pathlib import Path
from typing import Dict, Iterator, List

from . import config, net
from .util import file_hash

# Espera base entre tentativas de download, em segundos. Os testes zeram.
RETRY_DELAY = 10

FILE_NAME = "carcara-recursos.tar.gz"

# As fontes que os estilos de referência do esquema pedem para rótulos em escrita latina. A origem tem também uma
# fonte para a escrita devanágari (quatro faixas próprias e o resto em links para a Noto Sans Regular); ela fica de
# fora inteira: só um estilo gerado para hindi, marata ou nepalês a pede.
FONTSTACKS = ("Noto Sans Regular", "Noto Sans Medium", "Noto Sans Italic")
# As variações de cor das folhas de ícones, cada uma em 1x e 2x, com o índice (.json) e a imagem (.png).
SPRITE_FLAVORS = ("light", "dark", "white", "grayscale", "black")
SPRITES_FOLDER = f"sprites/v{config.TILESET_MAJOR_VERSION}/"

FONTS_LICENCE = "fonts/OFL.txt"
ICONS_LICENCE = "sprites/LICENCA.md"
README = "LEIAME.md"


def ranges() -> Iterator[str]:
    """Os nomes das 256 faixas de 256 caracteres: '0-255', '256-511', ..., '65280-65535'."""
    for start in range(0, 65536, 256):
        yield f"{start}-{start + 255}"


def required() -> List[str]:
    """Todo arquivo que um estilo de referência pode pedir."""
    names = [f"fonts/{stack}/{glyph_range}.pbf" for stack in FONTSTACKS for glyph_range in ranges()]
    names += [f"{SPRITES_FOLDER}{flavor}{density}.{extension}" for flavor in SPRITE_FLAVORS
              for density in ("", "@2x") for extension in ("json", "png")]
    return names + [FONTS_LICENCE]


def _wanted(name: str) -> bool:
    # Só três níveis, com os dois primeiros fixos: não há como um caminho com ".." passar daqui.
    parts = name.split("/")
    if name == FONTS_LICENCE:
        return True
    if len(parts) == 3 and parts[0] == "fonts" and parts[1] in FONTSTACKS and parts[2].endswith(".pbf"):
        return True
    return len(parts) == 3 and name.startswith(SPRITES_FOLDER) and parts[2].endswith((".json", ".png"))


def select(files: Dict[str, bytes]) -> Dict[str, bytes]:
    """Do que o repositório de origem tem, só o que entra no pacote, com o mesmo caminho."""
    return {name: data for name, data in files.items() if _wanted(name)}


def content_digest(files: Dict[str, bytes]) -> str:
    """sha256 do conteúdo (nomes e bytes, em ordem): não depende de como o arquivo de origem foi empacotado."""
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode("utf-8") + b"\0" + hashlib.sha256(files[name]).digest())
    return h.hexdigest()


def _read_upstream(archive: Path) -> Dict[str, bytes]:
    """{caminho sem a pasta de cima: bytes} dos arquivos comuns do arquivo de origem. Links ficam de fora."""
    files = {}
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                if not member.isfile() or "/" not in member.name:
                    continue
                extracted = tar.extractfile(member)
                if extracted is not None:
                    files[member.name.split("/", 1)[1]] = extracted.read()
    except (tarfile.TarError, OSError, EOFError) as e:
        raise RuntimeError(f"o arquivo de recursos baixado não é um .tar.gz válido: {archive.name} ({e})") from e
    return files


def _readme(revision: str) -> bytes:
    return f"""# Recursos do mapa: fontes e ícones

Fontes dos rótulos e folhas de ícones para desenhar tiles no esquema do basemap da Protomaps, versão
{config.TILESET_MAJOR_VERSION}.

Origem: https://github.com/protomaps/basemaps-assets, revisão {revision}.

## Como usar num estilo

    "glyphs": "<endereço>/fonts/{{fontstack}}/{{range}}.pbf"
    "sprite": "<endereço>/sprites/v{config.TILESET_MAJOR_VERSION}/light"

Fontes: {", ".join(FONTSTACKS)}.
Ícones: {", ".join(SPRITE_FLAVORS)}, cada um em 1x e 2x.

## Licenças

- Fontes (fonts/): Noto Sans, SIL Open Font License 1.1. Texto em fonts/OFL.txt.
- Ícones (sprites/): derivados de um conjunto de ícones sob a licença MIT. Texto em sprites/LICENCA.md.
""".encode("utf-8")


def write_archive(files: Dict[str, bytes], dest: Path) -> None:
    """Grava o .tar.gz de forma reproduzível: ordem fixa, datas zeradas, e o gzip sem nome nem data."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as raw_file:
        with gzip.GzipFile(filename="", fileobj=raw_file, mode="wb", compresslevel=6, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for name in sorted(files):
                    info = tarfile.TarInfo(name)
                    info.size = len(files[name])
                    info.mtime = 0
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(files[name]))


def build(dist: Path) -> Dict[str, object]:
    """Monta `carcara-recursos.tar.gz` em `dist`. Devolve {path, file, bytes, sha256, revision, glyph_files,
    sprite_files}."""
    revision = config.ASSETS_REVISION
    config.RAW.mkdir(parents=True, exist_ok=True)
    upstream = config.RAW / f"basemaps-assets-{revision}.tar.gz"
    if not upstream.exists():
        print(f"[recursos] baixando a revisão {revision[:12]}...")
        net.download(config.ASSETS_ARCHIVE_URL.format(revision=revision), upstream, identity=revision,
                     delay=RETRY_DELAY)
    try:
        files = select(_read_upstream(upstream))
    except RuntimeError:
        upstream.unlink(missing_ok=True)  # não deixa um download estragado valendo para a próxima vez
        raise

    missing = [name for name in required() if name not in files]
    if missing:
        raise RuntimeError(f"faltam {len(missing)} arquivos nos recursos da revisão {revision[:12]}: "
                           f"{', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
    found = content_digest(files)
    if found != config.ASSETS_CONTENT_SHA256:
        raise RuntimeError(f"o conteúdo dos recursos da revisão {revision[:12]} não é o conferido: {found}, "
                           f"esperado {config.ASSETS_CONTENT_SHA256} (ASSETS_CONTENT_SHA256 em carcara/config.py)")

    packed = dict(files)
    packed[ICONS_LICENCE] = (config.GENERATOR_DIR / "licencas" / "ICONES_MIT.md").read_bytes()
    packed[README] = _readme(revision)
    dest = dist / FILE_NAME
    write_archive(packed, dest)
    return {"path": dest, "file": FILE_NAME, "bytes": dest.stat().st_size, "sha256": file_hash(dest),
            "revision": revision,
            "glyph_files": sum(1 for name in files if name.endswith(".pbf")),
            "sprite_files": sum(1 for name in files if name.startswith(SPRITES_FOLDER))}

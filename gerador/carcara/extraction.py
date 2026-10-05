"""O recorte com o `pmtiles extract`, e a leitura do que a ferramenta informa.

- A simulação (`--dry-run`): a ferramenta lê os diretórios do arquivo de origem, conta os tiles da área e diz o
  tamanho que o recorte teria, sem baixar nenhum tile.
- O recorte de verdade: copia os tiles da área para um arquivo novo. Grava num nome provisório, e o nome final só
  aparece com o arquivo inteiro.
- O cabeçalho, os metadados e a conferência (`verify`) de um arquivo já recortado.

A origem pode ser um endereço (o build da Protomaps) ou um arquivo local (o pacote leve sai do completo).
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import config

# Os tamanhos saem arredondados, em unidades decimais ("48 MB", "1.2 GB", "950 kB").
_UNITS = {"B": 1, "kB": 10 ** 3, "MB": 10 ** 6, "GB": 10 ** 9, "TB": 10 ** 12}
_SIZE = r"([0-9]+(?:\.[0-9]+)?) ([A-Za-z]+)"
_TILES = re.compile(r"Region tiles (\d+), result tile entries (\d+)")
_REQUESTS = re.compile(r"Extract required (\d+) total requests")
_SUMMARY = re.compile(rf"Extract transferred {_SIZE} \(overfetch [0-9.]+\) for an archive size of {_SIZE}")
_COUNTS = {"addressed_tiles": re.compile(r"^addressed tiles count: (\d+)\s*$", re.MULTILINE),
           "tile_entries": re.compile(r"^tile entries count: (\d+)\s*$", re.MULTILINE),
           "tile_contents": re.compile(r"^tile contents count: (\d+)\s*$", re.MULTILINE)}
_CLUSTERED = re.compile(r"^clustered: (true|false)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Estimate:
    """O que um recorte teria, pela simulação."""
    region_tiles: int        # tiles endereçados dentro da área
    tile_entries: int        # entradas no arquivo de saída (tiles repetidos contam uma vez)
    archive_bytes: int       # tamanho do arquivo de saída, como a ferramenta arredondou
    archive_resolution: int  # o quanto vale o último algarismo escrito em `archive_bytes`
    transfer_bytes: int      # o que seria baixado, com a folga do `--overfetch`
    requests: int            # pedidos HTTP do recorte inteiro


@dataclass(frozen=True)
class Header:
    """O cabeçalho de um arquivo PMTiles."""
    tile_type: str                              # "mvt"
    tile_compression: str                       # "gzip"
    minzoom: int
    maxzoom: int
    bounds: Tuple[float, float, float, float]   # oeste, sul, leste, norte: o retângulo da área pedida no recorte
    addressed_tiles: int                        # tiles que o arquivo atende
    tile_entries: int                           # entradas no diretório (sequências de tiles iguais contam uma vez)
    tile_contents: int                          # conteúdos distintos guardados
    clustered: bool


def _size(number: str, unit: str) -> tuple:
    """(bytes, resolução em bytes) de um tamanho escrito pela ferramenta."""
    if unit not in _UNITS:
        raise ValueError(f"unidade de tamanho desconhecida na saída do pmtiles: {unit!r}")
    decimals = len(number.split(".")[1]) if "." in number else 0
    return round(float(number) * _UNITS[unit]), _UNITS[unit] // 10 ** decimals


def parse_dry_run(output: str) -> Estimate:
    """Lê a saída do `pmtiles extract --dry-run`."""
    tiles, requests, summary = _TILES.search(output), _REQUESTS.search(output), _SUMMARY.search(output)
    if not (tiles and requests and summary):
        raise ValueError(f"saída do pmtiles extract sem o resumo esperado:\n{output}")
    transfer_bytes, _ = _size(summary.group(1), summary.group(2))
    archive_bytes, archive_resolution = _size(summary.group(3), summary.group(4))
    return Estimate(region_tiles=int(tiles.group(1)), tile_entries=int(tiles.group(2)),
                    archive_bytes=archive_bytes, archive_resolution=archive_resolution,
                    transfer_bytes=transfer_bytes, requests=int(requests.group(1)))


def format_size(size: int, resolution: int) -> str:
    """O tamanho em MB, só com as casas que a ferramenta informou: '48 MB', '6,1 MB', '0,334 MB'."""
    decimals = 0
    while resolution * 10 ** decimals < 10 ** 6:
        decimals += 1
    return f"{size / 10 ** 6:.{decimals}f} MB".replace(".", ",")


def dry_run(source: str, region: Path, maxzoom: int) -> Estimate:
    """Simula o recorte de `region` (GeoJSON) em `source` (arquivo ou endereço) até `maxzoom`. Não baixa tiles."""
    # O nome de saída é obrigatório na linha de comando, mas a simulação não grava nada.
    command = [config.PMTILES, "extract", source, "simulacao.pmtiles", f"--region={region}",
               f"--maxzoom={maxzoom}", f"--download-threads={config.DOWNLOAD_THREADS}", "--dry-run"]
    done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise RuntimeError(f"pmtiles extract falhou (código {done.returncode}):\n{done.stdout}")
    return parse_dry_run(done.stdout)


def _run(arguments: list) -> subprocess.CompletedProcess:
    return subprocess.run([config.PMTILES, *arguments], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace")


def extract(source: str, dest: Path, maxzoom: int, region: Optional[Path] = None) -> Estimate:
    """Recorta `source` (endereço ou arquivo) até `maxzoom` para `dest`; com `region` (GeoJSON), só a área dela.

    Devolve o resumo que a ferramenta escreve. Se falhar, não deixa nem `dest` nem o arquivo provisório."""
    partial = dest.with_name(dest.name + ".parcial")
    partial.unlink(missing_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    arguments = ["extract", source, str(partial), f"--maxzoom={maxzoom}",
                 f"--download-threads={config.DOWNLOAD_THREADS}"]
    if region is not None:
        arguments.append(f"--region={region}")
    try:
        done = _run(arguments)
        if done.returncode != 0:
            raise RuntimeError(f"pmtiles extract falhou (código {done.returncode}):\n{_last_lines(done.stdout)}")
        if not partial.exists():
            raise RuntimeError(f"pmtiles extract terminou sem gravar o arquivo:\n{_last_lines(done.stdout)}")
        summary = parse_dry_run(done.stdout)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(dest)
    return summary


def _last_lines(output: str, count: int = 5) -> str:
    """O fim da saída da ferramenta, sem as linhas de progresso (que ela reescreve no lugar)."""
    lines = [line for line in output.replace("\r", "\n").splitlines()
             if line.strip() and "fetching chunks" not in line]
    return "\n".join(lines[-count:])


def verify(path: Path) -> None:
    """Confere a estrutura do arquivo (`pmtiles verify`). Lança se ele estiver truncado ou não for PMTiles."""
    done = _run(["verify", str(path)])
    if done.returncode != 0:
        raise RuntimeError(f"pmtiles verify recusou {path.name}:\n{_last_lines(done.stdout)}")


def parse_header(header_json: str, show_text: str) -> Header:
    """Junta o que o `pmtiles show --header-json` e o `pmtiles show` dizem do mesmo arquivo."""
    try:
        data = json.loads(header_json)
        bounds = tuple(float(v) for v in data["bounds"])
        counts = {name: pattern.search(show_text) for name, pattern in _COUNTS.items()}
        clustered = _CLUSTERED.search(show_text)
        if len(bounds) != 4 or clustered is None or not all(counts.values()):
            raise KeyError("contagens")
        return Header(tile_type=str(data["tile_type"]), tile_compression=str(data["tile_compression"]),
                      minzoom=int(data["minzoom"]), maxzoom=int(data["maxzoom"]), bounds=bounds,
                      clustered=clustered.group(1) == "true",
                      **{name: int(match.group(1)) for name, match in counts.items()})
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"cabeçalho do pmtiles em formato inesperado ({e.__class__.__name__}: {e})") from e


def header(path: Path) -> Header:
    """O cabeçalho de um arquivo local."""
    as_json, as_text = _run(["show", str(path), "--header-json"]), _run(["show", str(path)])
    if as_json.returncode != 0 or as_text.returncode != 0:
        raise RuntimeError(f"pmtiles show recusou {path.name}:\n{_last_lines(as_json.stdout or as_text.stdout)}")
    try:
        return parse_header(as_json.stdout, as_text.stdout)
    except ValueError as e:
        raise RuntimeError(f"{path.name}: {e}") from e


def metadata(path: Path) -> Dict[str, object]:
    """Os metadados que o arquivo carrega: versão do esquema, crédito, data dos dados, lista de camadas."""
    done = subprocess.run([config.PMTILES, "show", str(path), "--metadata"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    try:
        if done.returncode != 0:
            raise ValueError(done.stderr)
        data = json.loads(done.stdout)
        if not isinstance(data, dict):
            raise ValueError("não é um objeto")
        return data
    except ValueError as e:
        raise RuntimeError(f"pmtiles show --metadata recusou {path.name}: {str(e)[:300]}") from e


def set_attribution(path: Path, text: str) -> None:
    """Troca o crédito (`attribution`) dos metadados de `path` por `text`; o resto dos metadados e os tiles ficam."""
    data = metadata(path)
    data["attribution"] = text
    with tempfile.TemporaryDirectory() as folder:
        new = Path(folder) / "metadados.json"
        new.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        done = _run(["edit", str(path), "--metadata", str(new)])
    if done.returncode != 0:
        raise RuntimeError(f"pmtiles edit recusou {path.name}:\n{_last_lines(done.stdout)}")


def read_tile(path: Path, z: int, x: int, y: int) -> Optional[bytes]:
    """Os bytes de um tile como estão no arquivo (compactados), ou None se o arquivo não tem esse tile."""
    done = subprocess.run([config.PMTILES, "tile", str(path), str(z), str(x), str(y)], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    if done.returncode != 0:
        raise RuntimeError(f"pmtiles tile falhou em {path.name} {z}/{x}/{y}: "
                           f"{done.stderr.decode('utf-8', 'replace')[-300:]}")
    return done.stdout or None

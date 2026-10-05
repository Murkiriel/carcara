"""O binário `pmtiles`: qual versão está instalada, e como instalar a versão fixada.

O gerador lê o que a ferramenta escreve, e isso foi conferido numa versão. Por isso a versão é fixada no config, o
arquivo baixado é conferido pelo sha256 publicado na release, e uma versão diferente é recusada antes de qualquer
recorte.
"""
from __future__ import annotations

import os
import platform
import re
import stat
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from . import config, net
from .util import file_hash

# Espera base entre tentativas de download, em segundos. Os testes zeram.
RETRY_DELAY = 10

_MACHINES = {"amd64": "x86_64", "x86_64": "x86_64", "x64": "x86_64"}
_VERSION = re.compile(r"^pmtiles (\d+\.\d+\.\d+)\b", re.MULTILINE)


def asset_for(system: Optional[str] = None, machine: Optional[str] = None) -> Tuple[str, str]:
    """(nome do arquivo na release, sha256) para o sistema e o processador dados, ou os desta máquina."""
    system = system or platform.system()
    machine = machine or platform.machine()
    key = (system, _MACHINES.get(machine.lower(), machine))
    if key not in config.PMTILES_ASSETS:
        raise RuntimeError(f"não há binário do pmtiles {config.PMTILES_VERSION} fixado para {system} {machine}; "
                           f"instale essa versão à mão e aponte CARCARA_PMTILES para ela")
    return config.PMTILES_ASSETS[key]


def _binary_name(system: str) -> str:
    return "pmtiles.exe" if system == "Windows" else "pmtiles"


def _read_member(archive: Path, member: str) -> Optional[bytes]:
    """Os bytes do membro chamado exatamente `member`, ou None. Nada do arquivo é extraído para o disco."""
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            return z.read(member) if member in z.namelist() else None
    with tarfile.open(archive, "r:gz") as t:
        for info in t:
            if info.name == member and info.isfile():
                extracted = t.extractfile(info)
                return extracted.read() if extracted is not None else None
    return None


def install(folder: Path, system: Optional[str] = None, machine: Optional[str] = None) -> Path:
    """Baixa o `pmtiles` da versão fixada, confere o sha256 e deixa só o binário em `folder`. Devolve o caminho."""
    system = system or platform.system()
    name, sha256 = asset_for(system, machine)
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / name
    try:
        net.download(config.PMTILES_RELEASE_URL + name, archive, identity=sha256, delay=RETRY_DELAY)
        found = file_hash(archive)
        if found != sha256:
            raise RuntimeError(f"sha256 do {name} não confere: {found}, esperado {sha256}")
        binary_name = _binary_name(system)
        content = _read_member(archive, binary_name)
        if content is None:
            raise RuntimeError(f"o {name} não tem o arquivo {binary_name}")
    finally:
        archive.unlink(missing_ok=True)
    binary = folder / binary_name
    binary.write_bytes(content)
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return binary


def installed_version(binary: Optional[str] = None) -> str:
    """A versão que o binário informa (`pmtiles version`)."""
    done = subprocess.run([binary or config.PMTILES, "version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace")
    match = _VERSION.search(done.stdout or "")
    if done.returncode != 0 or not match:
        raise RuntimeError(f"não consegui ler a versão do pmtiles:\n{done.stdout}")
    return match.group(1)


def require(binary: Optional[str] = None) -> None:
    """Para com uma mensagem clara se o `pmtiles` não está instalado ou não é a versão fixada."""
    binary = binary or config.PMTILES
    try:
        version = installed_version(binary)
    except FileNotFoundError as e:
        raise RuntimeError(f"o pmtiles não foi encontrado ({binary}); instale com `python scripts/install_pmtiles.py` "
                           f"e aponte CARCARA_PMTILES para o binário") from e
    if version != config.PMTILES_VERSION:
        raise RuntimeError(f"o pmtiles instalado é o {version}; o gerador foi conferido com o "
                           f"{config.PMTILES_VERSION} (carcara/config.py)")


def export_to_actions(binary: Path, env_file: Optional[str]) -> None:
    """No GitHub Actions, deixa CARCARA_PMTILES definida para os passos seguintes do job."""
    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(f"CARCARA_PMTILES={binary}\n")

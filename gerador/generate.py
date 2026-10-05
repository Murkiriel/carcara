"""Gera os pacotes de uma geração em data/dist/: um por estado, o leve de cada um, a base e os recursos.

    python generate.py                     # as 27 UFs: baixa cerca de 4,8 GB do build da Protomaps
    python generate.py --states DF,GO      # só estas UFs (e a base): para desenvolver e testar
    python generate.py --no-light          # sem os pacotes leves
    python generate.py --accept-drop       # passa por cima da trava de queda (pacote que encolheu)

Etapas, em ordem: prepare (confere a ferramenta, baixa a malha do IBGE, monta os polígonos, escolhe o build),
packs (recorta), resources (ícones e fontes), validate (as travas de carcara/validation.py), catalog (escreve
data/dist/catalogo.json). O que já foi recortado do mesmo build é reaproveitado: se a geração cair no meio, rodar
de novo continua de onde parou.

Se uma trava barra, o comando termina com código 1, lista os problemas, deixa a marca GERACAO_EM_ANDAMENTO e não
escreve o catálogo.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# Pythons sem venv podem instalar as dependências com `pip install --target .pylib -r requirements.txt`; esta pasta
# entra no caminho de import se existir.
if (HERE / ".pylib").exists():
    sys.path.insert(0, str(HERE / ".pylib"))

from carcara import (catalog, config, extraction, packs, pmtiles_tool, regions, resources, run_record,  # noqa: E402
                     sources, validation)

CATALOG = "catalogo.json"


class ValidationFailed(Exception):
    """Uma ou mais travas barraram a geração."""

    def __init__(self, problems: List[str]) -> None:
        super().__init__(f"{len(problems)} problema(s) na validação")
        self.problems = problems


def parse_states(option: Optional[str]) -> List[str]:
    """As UFs pedidas em `--states`, em maiúsculas e em ordem; sem a opção, as 27."""
    if option is None:
        return sorted(config.STATES)
    states = sorted({part.strip().upper() for part in option.split(",") if part.strip()})
    unknown = [state for state in states if state not in config.STATES]
    if unknown:
        raise ValueError(f"UF desconhecida em --states: {', '.join(unknown)}")
    if not states:
        raise ValueError("--states veio vazio")
    return states


def check_disk_space(folder: Path, minimum: int = config.MIN_FREE_DISK_BYTES, free: Optional[int] = None) -> None:
    """Para na hora se a unidade de `folder` não tem `minimum` bytes livres (`free` injetável nos testes)."""
    if free is None:
        folder.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(folder).free
    if free < minimum:
        raise RuntimeError(f"só {free / 1e9:.1f} GB livres na unidade de {folder}; a geração precisa de "
                           f"{minimum / 1e9:.0f} GB")


def published_catalog() -> Optional[dict]:
    """O catálogo da geração publicada (na raiz do repositório), ou None se nenhuma foi publicada ainda."""
    path = config.REPO / CATALOG
    if not path.exists():
        return None
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(catalog, dict):
            raise ValueError("não é um objeto")
        return catalog
    except (OSError, ValueError) as e:
        raise RuntimeError(f"não consegui ler o catálogo publicado ({path}): {e}") from e


def _utf8_output() -> None:
    # Log redirecionado para arquivo sai na codificação do sistema e os acentos quebram; UTF-8 sempre.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def run(states: List[str], recorder: run_record.RunRecorder, light: bool, accept_drop: bool = False) -> str:
    """As etapas da geração. Devolve o resumo de uma linha; lança ValidationFailed se uma trava barrar."""
    partial = sorted(states) != sorted(config.STATES)
    with recorder.stage("prepare"):
        pmtiles_tool.require()
        check_disk_space(config.DATA)
        mesh = sources.ibge_mesh()
        region_paths = regions.write_regions(mesh, config.REGIONS)
        build = sources.latest_build()
        build_id = sources.build_id(build)
        published = published_catalog()
        print(f"[gerar] geração {build_id}: build {build['key']} ({build['uploaded']}, esquema {build['version']})")
    recorder.note("build_id", build_id)
    recorder.note("build", build)
    recorder.note("states", states)
    recorder.note("partial", partial)
    with recorder.stage("packs"):
        generated = packs.generate(build, region_paths, states, config.DIST, light=light)
    with recorder.stage("resources"):
        pack = resources.build(config.DIST)

    full = sum(int(p["bytes"]) for p in generated.values())
    lights = sum(int(p["light"]["bytes"]) for p in generated.values() if p.get("light"))
    transferred = sum(int(p["transfer_bytes"]) for p in generated.values())
    recorder.note("transfer_bytes", transferred)
    recorder.note("packs_bytes", full + lights + int(pack["bytes"]))

    polygons = regions.state_polygons(mesh)
    with recorder.stage("validate"):
        problems = validation.validate(dist=config.DIST, generated=generated, resources_pack=pack, build=build,
                                       polygons=polygons, states=states, light=light,
                                       published=published, accept_drop=accept_drop)
        if problems:
            raise ValidationFailed(problems)
    with recorder.stage("catalog"):
        # A data dos dados do OpenStreetMap vem dos metadados que os pacotes herdam do build.
        metadata = extraction.metadata(config.DIST / str(generated[packs.BASE]["file"]))
        osm_timestamp = str(metadata.get("planetiler:osm:osmosisreplicationtime") or "")
        catalog.save(catalog.build_catalog(build, generated, pack, polygons, osm_timestamp=osm_timestamp),
                     config.DIST / CATALOG)

    plural = "estado" if len(states) == 1 else "estados"
    summary = (f"geração {build_id}: {len(states)} {plural} e a base com {full / 1e9:.2f} GB, leves com "
               f"{lights / 1e9:.2f} GB, recursos com {int(pack['bytes']) / 1e6:.1f} MB; {transferred / 1e9:.2f} GB "
               f"baixados do build; validação sem problemas")
    return summary + ("; geração parcial, não publicável" if partial else "")


def main(argv: Optional[List[str]] = None) -> int:
    _utf8_output()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--states", help="UFs separadas por vírgula (padrão: as 27)")
    parser.add_argument("--no-light", action="store_true", help="não gera os pacotes leves")
    parser.add_argument("--accept-drop", action="store_true",
                        help="aceita pacote que encolheu além da tolerância em relação à geração publicada")
    args = parser.parse_args(argv)
    try:
        states = parse_states(args.states)
    except ValueError as e:
        print(f"[gerar] {e}", file=sys.stderr)
        return 2

    config.DIST.mkdir(parents=True, exist_ok=True)
    marker = config.DIST / config.IN_PROGRESS_MARKER
    marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    recorder = run_record.RunRecorder(config.DATA)
    if args.accept_drop:
        print("[gerar] AVISO: --accept-drop ligado; a trava de queda só registra, não barra")
    result = "failed"
    try:
        summary = run(states, recorder, light=config.LIGHT_PACKS and not args.no_light, accept_drop=args.accept_drop)
        result = "ok"
    except ValidationFailed as e:
        result = "failed: validation"
        recorder.note("problems", e.problems)
        print("\n[gerar] A VALIDAÇÃO BARROU A GERAÇÃO:")
        for problem in e.problems:
            print("  -", problem)
        return 1
    except BaseException as e:
        result = f"failed: {e.__class__.__name__}: {e}"
        raise
    finally:
        recorder.save(config.DIST / "geracao.json", result)
    minutes = sum(stage["minutes"] for stage in recorder.stages)
    print(f"\n[gerar] {summary}, em {minutes:.1f} min; pico de disco em data/: {recorder.peak / 1e9:.1f} GB "
          f"(detalhes em data/dist/geracao.json)")
    marker.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())

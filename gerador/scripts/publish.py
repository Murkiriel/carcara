"""Publica a geração de data/dist/: sobe os pacotes numa release do GitHub e grava o catalogo.json na raiz.

    python scripts/publish.py                  # só confere (nada é publicado)
    python scripts/publish.py --release        # confere, sobe a release <build_id> e grava o catálogo
    python scripts/publish.py --release --commit --push   # e ainda faz commit e push do catálogo e do README
    python scripts/publish.py --accept-drop    # passa por cima da trava de queda
    python scripts/publish.py --accept-older   # publica uma geração de um build mais antigo que o da publicada
    python scripts/publish.py --prune --dry-run   # só lista as releases antigas que a limpeza apagaria
    python scripts/publish.py --prune          # apaga as releases antigas (a publicação com --push já faz isso)

A ordem importa: primeiro os pacotes sobem para a release, só depois o catalogo.json e a tabela de downloads do
README mudam (os dois no mesmo commit). Assim ninguém lê um catálogo que aponta para arquivos que ainda não existem.
A release sobe como rascunho e só é publicada com todos os arquivos presentes, do tamanho certo e com o sha256 do
catálogo; se a subida cair no meio, rodar de novo retoma do que falta. Usa o `gh` (GitHub CLI) já logado.

Não publica se:
- a geração ainda roda ou caiu no meio (marca GERACAO_EM_ANDAMENTO em data/dist/),
- a geração é parcial (faltam UFs no catálogo),
- o catálogo é de outro schema ou de outra versão maior do esquema dos tiles,
- algum arquivo falta, não bate o tamanho ou o sha256, ou passa do limite de um arquivo de release,
- algum pacote perdeu mais de 5% dos tiles ou dos bytes em relação ao catalogo.json publicado (--accept-drop),
- a geração vem de um build mais antigo que o da publicada (--accept-older),
- já existe uma release PUBLICADA com o mesmo build_id (um rascunho é retomado),
- com --commit, o git do repositório não está com o e-mail anônimo do GitHub.

Depois do push do catálogo novo, as releases antigas são apagadas: ficam a do catálogo e as anteriores mais recentes,
config.KEEP_GENERATIONS no total. Só depois do push, porque até ali o catálogo publicado ainda aponta para a geração
anterior. Se a limpeza falhar, vira aviso: a geração já está publicada, e a próxima publicação tenta de novo.

A lógica fica em carcara/publishing.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, publishing  # noqa: E402

CATALOG = "catalogo.json"


def prune(dry_run: bool) -> int:
    """O modo --prune: a limpeza das releases antigas sozinha, pela geração do catalogo.json da raiz."""
    root_catalog = config.REPO / CATALOG
    if not root_catalog.exists():
        print("Sem catalogo.json na raiz: nada publicado, nada a apagar.", file=sys.stderr)
        return 1
    tag = json.loads(root_catalog.read_text(encoding="utf-8"))["build_id"]
    try:
        doomed = publishing.prune_releases(publishing.gh_real, tag, config.KEEP_GENERATIONS, dry_run)
    except (publishing.GhError, publishing.PruneRefused) as e:
        print(f"Limpeza não feita: {e}", file=sys.stderr)
        return 1
    kept = f"catálogo em {tag}, ficam {config.KEEP_GENERATIONS} gerações"
    if not doomed:
        print(f"Nenhuma release antiga a apagar ({kept}).")
    elif dry_run:
        print(f"Apagaria ({kept}): {', '.join(doomed)}.")
    else:
        print(f"Releases antigas apagadas ({kept}): {', '.join(doomed)}.")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # acentos certos também com a saída redirecionada para arquivo
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", action="store_true", help="sobe a release e grava o catalogo.json na raiz")
    parser.add_argument("--commit", action="store_true", help="commit do catalogo.json e do README (exige --release)")
    parser.add_argument("--push", action="store_true", help="push do commit (exige --commit)")
    parser.add_argument("--accept-drop", action="store_true", help="publica mesmo com pacote que encolheu")
    parser.add_argument("--accept-older", action="store_true",
                        help="publica mesmo vindo de um build mais antigo que o da geração publicada")
    parser.add_argument("--prune", action="store_true",
                        help=f"só apaga as releases antigas (ficam {config.KEEP_GENERATIONS} gerações); não publica")
    parser.add_argument("--dry-run", action="store_true", help="com --prune: lista o que apagaria, sem apagar")
    args = parser.parse_args()
    problem = publishing.flags_problem(args.release, args.commit, args.push, args.prune, args.dry_run)
    if problem:
        parser.error(problem)
    if args.prune:
        return prune(args.dry_run)

    generated = config.DIST / CATALOG
    if not generated.exists():
        print(f"Sem {generated}: rode python generate.py antes.", file=sys.stderr)
        return 1
    cat = json.loads(generated.read_text(encoding="utf-8"))
    root_catalog = config.REPO / CATALOG
    published = json.loads(root_catalog.read_text(encoding="utf-8")) if root_catalog.exists() else None

    problems = publishing.check(cat, published, config.DIST, args.accept_drop, args.accept_older)
    if args.commit:
        identity = publishing.commit_identity_problem(publishing.git_real)
        if identity:
            problems.append(identity)
    if problems:
        print("Não publicado:")
        for found in problems:
            print("  -", found)
        return 1
    entries = publishing.files(cat)
    total = sum(entry["bytes"] for entry in entries)
    print(f"Geração {cat['build_id']} conferida: {len(entries)} arquivos, {total / 1e9:.2f} GB, esquema "
          f"{cat['tileset']['version']}, build de {cat['source']['timestamp']}")
    if not args.release:
        print("Nada publicado (use --release).")
        return 0
    try:
        publishing.publish_generation(cat, config.DIST, config.REPO, publishing.gh_real, publishing.git_real,
                                      commit=args.commit, push=args.push, keep=config.KEEP_GENERATIONS)
    except (publishing.GhError, publishing.GitError, publishing.ReleaseAlreadyPublished) as e:
        print(f"Publicação interrompida: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

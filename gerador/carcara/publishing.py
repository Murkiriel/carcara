"""As travas e a subida da publicação: o que precisa estar certo antes de uma geração ir para a release e para o
catálogo, e a própria release.

A linha de comando fica em scripts/publish.py; aqui só a lógica, testável sem o GitHub: o `gh` entra como uma função
`gh(args) -> (código, stdout, stderr)` e o `git` como `git(*args) -> (código, stdout, stderr)`, e os testes passam
versões falsas.

A release é criada como RASCUNHO, sem arquivos; cada pacote que ainda não está lá (ou está com outro tamanho ou
outro conteúdo) sobe; só com todos presentes, do tamanho certo e com o sha256 que o catálogo diz, ela é publicada.
Uma queda no meio deixa um rascunho que ninguém vê, e rodar de novo retoma do que falta. Release já publicada com a
mesma etiqueta não é mexida.

Só depois de a release estar no ar o catalogo.json e a tabela de downloads do README mudam: ninguém lê um catálogo
que aponta para arquivos que ainda não existem. E só depois do push desse catálogo as releases antigas são apagadas
(`prune_releases`): ficam a do catálogo e as anteriores mais recentes.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import catalog, config, validation
from .util import file_hash

Gh = Callable[[Sequence[str]], Tuple[int, str, str]]
Git = Callable[..., Tuple[int, str, str]]

ANONYMOUS_SUFFIX = "@users.noreply.github.com"
ROOT_FILES = ["catalogo.json", "README.md"]


class GhError(RuntimeError):
    """Um comando do gh falhou; a mensagem traz o comando e o que o gh disse."""


class GitError(RuntimeError):
    """Um comando do git falhou; a mensagem traz o comando e o que o git disse."""


class ReleaseAlreadyPublished(RuntimeError):
    """Já existe uma release publicada (não rascunho) com esta etiqueta."""


def gh_real(args: Sequence[str]) -> Tuple[int, str, str]:
    """O `gh` de verdade, no repositório do projeto."""
    done = subprocess.run(["gh", *args, "--repo", config.GITHUB_REPO], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return done.returncode, done.stdout, done.stderr


def git_real(*args: str) -> Tuple[int, str, str]:
    """O `git` de verdade, no repositório do projeto."""
    done = subprocess.run(["git", "-C", str(config.REPO), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    return done.returncode, done.stdout, done.stderr


def _run(gh: Gh, args: Sequence[str]) -> str:
    code, output, error = gh(list(args))
    if code != 0:
        raise GhError(f"gh {' '.join(args)} falhou (código {code}): {error.strip() or output.strip()}")
    return output


def release_state(gh: Gh, tag: str) -> Tuple[str, Dict[str, Tuple[int, Optional[str]]]]:
    """('inexistente' | 'rascunho' | 'publicada', {arquivo: (tamanho, sha256 ou None)}). Só 'release not found'
    conta como inexistente: sem rede ou sem login é erro, para nunca tentar criar uma release por engano."""
    args = ["release", "view", tag, "--json", "isDraft,assets"]
    code, output, error = gh(args)
    if code != 0:
        if "not found" in error.lower():
            return "inexistente", {}
        raise GhError(f"gh {' '.join(args)} falhou (código {code}): {error.strip() or output.strip()}")
    data = json.loads(output)
    assets = {}
    for asset in data.get("assets", []):
        digest = str(asset.get("digest") or "")
        assets[asset["name"]] = (int(asset["size"]), digest[7:] if digest.startswith("sha256:") else None)
    return ("rascunho" if data.get("isDraft") else "publicada"), assets


def publish_release(gh: Gh, tag: str, files: List[Tuple[Path, str]], title: str, notes: str) -> None:
    """Cria (ou retoma) o rascunho, sobe o que falta e publica. `files` = [(arquivo, sha256 esperado)].
    Levanta ReleaseAlreadyPublished ou GhError; enquanto algo não conferir, a release continua rascunho."""
    state, assets = release_state(gh, tag)
    if state == "publicada":
        raise ReleaseAlreadyPublished(f"a release {tag} já está publicada; gere de novo (outro build_id) "
                                      "ou apague-a antes")
    if state == "inexistente":
        _run(gh, ["release", "create", tag, "--draft", "--title", title, "--notes", notes])
        assets = {}
    for path, sha256 in files:
        size = path.stat().st_size
        if assets.get(path.name) == (size, sha256):
            continue  # já subiu inteiro numa tentativa anterior
        extra = ["--clobber"] if path.name in assets else []
        print(f"[release] subindo {path.name} ({size / 1e6:.1f} MB)...", flush=True)
        _run(gh, ["release", "upload", tag, str(path), *extra])
    _, assets = release_state(gh, tag)
    unverifiable = [path.name for path, _ in files if assets.get(path.name, (0, ""))[1] is None]
    if unverifiable:
        raise GhError(f"o GitHub não informou o sha256 de {', '.join(unverifiable[:5])} na release {tag}: não dá para "
                      "conferir o que subiu, e a release continua rascunho")
    wrong = [path.name for path, sha256 in files if assets.get(path.name) != (path.stat().st_size, sha256)]
    if wrong:
        raise GhError(f"a release {tag} continua sem {', '.join(wrong[:5])} (ou com outro tamanho ou outro conteúdo); "
                      "rode de novo")
    _run(gh, ["release", "edit", tag, "--draft=false"])


class PruneRefused(RuntimeError):
    """A limpeza não apaga nada: a release do catálogo publicado não está no ar."""


# Só releases com a etiqueta no formato do build_id (data + 8 primeiros caracteres do b3sum do build) são desta
# automação.
BUILD_ID_TAG = re.compile(r"^\d{4}-\d{2}-\d{2}-[0-9a-f]{8}$")


def _age_key(release: dict) -> Tuple[str, str]:
    """Ordem das gerações: a data do build_id e, no mesmo dia, a hora da publicação."""
    return release["tagName"][:10], release.get("publishedAt") or ""


def releases_to_delete(releases: List[dict], current_tag: str, keep: int) -> List[str]:
    """Etiquetas a apagar, da mais antiga para a mais nova. Ficam a release do catálogo publicado (`current_tag`) e
    as `keep - 1` gerações publicadas mais recentes além dela; saem as demais e os rascunhos órfãos (uma subida que
    caiu deixa um rascunho que a geração seguinte, com outro build_id, nunca retoma). Release com etiqueta fora do
    formato do build_id nunca entra. `keep` 0 (ou menos) desliga a limpeza."""
    if keep <= 0:
        return []
    ours = [r for r in releases if BUILD_ID_TAG.match(r["tagName"]) and r["tagName"] != current_tag]
    published = sorted((r for r in ours if not r.get("isDraft")), key=_age_key, reverse=True)
    doomed = published[keep - 1:] + [r for r in ours if r.get("isDraft")]
    return [r["tagName"] for r in sorted(doomed, key=_age_key)]


def prune_releases(gh: Gh, current_tag: str, keep: int, dry_run: bool = False) -> List[str]:
    """Apaga as releases antigas (e as etiquetas delas) e devolve as etiquetas apagadas; com `dry_run`, só devolve
    o que apagaria. Levanta PruneRefused, sem apagar nada, se a release do catálogo não estiver publicada: é o sinal
    de que o catálogo e as releases não batem."""
    if keep <= 0:
        return []
    releases = json.loads(_run(gh, ["release", "list", "--limit", "1000", "--json", "tagName,isDraft,publishedAt"]))
    current = next((r for r in releases if r["tagName"] == current_tag), None)
    if current is None or current.get("isDraft"):
        raise PruneRefused(f"a release {current_tag} do catálogo não está publicada; nenhuma release foi apagada")
    drafts = {r["tagName"] for r in releases if r.get("isDraft")}
    doomed = releases_to_delete(releases, current_tag, keep)
    if not dry_run:
        for tag in doomed:
            print(f"[release] apagando a release antiga {tag}...")
            # um rascunho ainda não tem etiqueta no git
            _run(gh, ["release", "delete", tag, "--yes"] + ([] if tag in drafts else ["--cleanup-tag"]))
    return doomed


def prune_after_publish(gh: Gh, current_tag: str, keep: int) -> Tuple[List[str], Optional[str]]:
    """A limpeza no fim de uma publicação: (etiquetas apagadas, aviso). Nunca levanta: a geração já está publicada,
    e o que falhar aqui a próxima publicação tenta de novo."""
    try:
        return prune_releases(gh, current_tag, keep), None
    except (GhError, PruneRefused, ValueError, KeyError, TypeError) as e:
        return [], f"releases antigas não apagadas: {e}"


def identity_problem(email: str) -> Optional[str]:
    """Commits do projeto só com o e-mail anônimo do GitHub."""
    if not email.strip().endswith(ANONYMOUS_SUFFIX):
        return f"o git deste repositório está com o e-mail '{email.strip()}', não o anônimo (*{ANONYMOUS_SUFFIX})"
    return None


def commit_identity_problem(git: Git) -> Optional[str]:
    """O mesmo, lendo o e-mail configurado no repositório."""
    return identity_problem(git("config", "user.email")[1])


def older_generation(published: Optional[dict], updated: dict) -> List[str]:
    """Barra publicar por cima uma geração feita de um build mais antigo que o da publicada."""
    if published and updated["source"]["timestamp"] < published["source"]["timestamp"]:
        return [f"a geração {updated['build_id']} vem de um build de {updated['source']['timestamp']}, mais antigo "
                f"que o da publicada ({published['build_id']}, {published['source']['timestamp']})"]
    return []


def flags_problem(release: bool, commit: bool, push: bool, prune: bool = False,
                  dry_run: bool = False) -> Optional[str]:
    if prune and (release or commit or push):
        return "--prune roda sozinho: a publicação (--release --commit --push) já faz a limpeza no fim"
    if dry_run and not prune:
        return "--dry-run só faz sentido com --prune"
    if commit and not release:
        return "--commit só faz sentido com --release (o catálogo só muda depois que a release sobe)"
    if push and not commit:
        return "--push só faz sentido com --commit"
    return None


def packs_of(cat: dict) -> Dict[str, dict]:
    """{'base': {...}, 'GO': {...}, ...}: os pacotes de tiles do catálogo, cada estado com o seu `light`."""
    return {"base": cat["base"], **cat["states"]}


def files(cat: dict) -> List[dict]:
    """Todo arquivo que a release precisa ter, com `file`, `bytes` e `sha256`: os recursos, a base, e o completo e o
    leve de cada estado."""
    out = [cat["resources"], cat["base"]]
    for state in sorted(cat["states"]):
        entry = cat["states"][state]
        out.append(entry)
        if entry.get("light"):
            out.append(entry["light"])
    return out


def check(cat: dict, published: Optional[dict], dist: Path, accept_drop: bool = False, accept_older: bool = False,
          log: Callable[[str], None] = print) -> List[str]:
    """Tudo o que impede publicar a geração `cat`, que está em `dist` (vazio = pode publicar)."""
    problems = []
    if (dist / config.IN_PROGRESS_MARKER).exists():
        problems.append("a geração ainda roda ou caiu no meio: rode python generate.py de novo")
    if cat.get("schema") != catalog.SCHEMA:
        problems.append(f"catálogo com schema {cat.get('schema')}; o gerador escreve o {catalog.SCHEMA}")
    if not BUILD_ID_TAG.match(str(cat.get("build_id"))):
        problems.append(f"build_id fora do formato AAAA-MM-DD-xxxxxxxx: {cat.get('build_id')!r}")
    version = str(cat["tileset"]["version"])
    if version.split(".")[0] != str(config.TILESET_MAJOR_VERSION):
        problems.append(f"catálogo do esquema {version}; o gerador só publica a versão maior "
                        f"{config.TILESET_MAJOR_VERSION}")
    missing_states = sorted(set(config.STATES) - set(cat["states"]))
    if missing_states:
        problems.append(f"geração parcial: faltam {len(missing_states)} das {len(config.STATES)} UFs "
                        f"({', '.join(missing_states)})")
    for entry in files(cat):
        path = dist / entry["file"]
        if not path.exists():
            problems.append(f"falta {entry['file']}")
        elif path.stat().st_size >= config.MAX_ASSET_BYTES:
            problems.append(f"{entry['file']}: {path.stat().st_size / 1e9:.2f} GB, acima do limite de um arquivo de "
                            "release")
        elif path.stat().st_size != entry["bytes"] or file_hash(path) != entry["sha256"]:
            problems.append(f"o tamanho ou o sha256 de {entry['file']} não bate com o catálogo")
    problems += validation.check_drop(packs_of(cat), published, accept_drop, log)
    if not accept_older:
        problems += older_generation(published, cat)
    return problems


def release_notes(cat: dict) -> str:
    return (f"Mapa base do Brasil por estado, em PMTiles, no esquema {cat['tileset']['name']} "
            f"{cat['tileset']['version']}. Recortado do build da Protomaps de {cat['source']['timestamp'][:10]}, com "
            f"dados do OpenStreetMap de {cat['source']['osm_timestamp'][:10]}. Índice: catalogo.json na raiz do "
            f"repositório.\n\n{cat['attribution']}")


def publish_generation(cat: dict, dist: Path, repo: Path, gh: Gh, git: Git, commit: bool, push: bool, keep: int,
                       log: Callable[[str], None] = print) -> None:
    """Sobe a release da geração `cat`, e só então grava o catálogo e a tabela do README em `repo`; com `commit`,
    faz o commit só desses dois arquivos; com `push`, envia e apaga as releases antigas."""
    tag = cat["build_id"]
    uploads = [(dist / entry["file"], entry["sha256"]) for entry in files(cat)]
    publish_release(gh, tag, uploads, f"Carcará {tag}", release_notes(cat))
    log(f"Release {tag} publicada com {len(uploads)} arquivos.")

    catalog.save(cat, repo / ROOT_FILES[0])
    readme = repo / ROOT_FILES[1]
    readme.write_text(catalog.update_readme(readme.read_text(encoding="utf-8"), catalog.downloads_table(cat)),
                      encoding="utf-8")
    log(f"catalogo.json e a tabela de downloads do README gravados ({repo})")
    if commit:
        commands = [["add", *ROOT_FILES], ["commit", "-m", f"Geração {tag}", "--", *ROOT_FILES]]
        for command in commands + ([["push"]] if push else []):
            code, output, error = git(*command)
            if code != 0:
                raise GitError(f"git {' '.join(command)} falhou: {error.strip() or output.strip()}")
    if push:  # só agora o catálogo publicado aponta para a geração nova
        deleted, warning = prune_after_publish(gh, tag, keep)
        if deleted:
            log(f"Releases antigas apagadas: {', '.join(deleted)}.")
        if warning:
            log(f"::warning::{warning}")

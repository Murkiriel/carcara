"""As travas da publicação e o fluxo inteiro, com `gh` e `git` falsos: NENHUM teste aqui publica nada."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import catalog, config, publishing  # noqa: E402
from tests.test_publishing_release import FakeGh  # noqa: E402

TAG = "2026-10-01-2b7e7669"
README = f"# Projeto\n\n{catalog.START_MARKER}\nNenhuma geração.\n{catalog.END_MARKER}\n\nresto\n"


class World(unittest.TestCase):
    """Uma geração completa de mentira em disco (as 27 UFs com um byte ou dois cada), e um repositório de mentira."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self._tmp.name) / "dist"
        self.repo = Path(self._tmp.name) / "repo"
        self.dist.mkdir()
        self.repo.mkdir()
        (self.repo / "README.md").write_text(README, encoding="utf-8")
        self.cat = self.catalog_of(sorted(config.STATES))
        catalog.save(self.cat, self.dist / "catalogo.json")
        self.log = []

    def tearDown(self):
        self._tmp.cleanup()

    def entry(self, name, tiles=1000, light=None):
        path = self.dist / name
        path.write_bytes(name.encode() * 3)
        entry = {"file": name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "tiles": tiles, "minzoom": 0, "maxzoom": 15}
        if light:
            entry["light"] = self.entry(light, tiles=300)
        return entry

    def catalog_of(self, states, build_id=TAG, timestamp="2026-10-01T08:53:09.033Z"):
        return {
            "schema": 1, "build_id": build_id, "built_at": "2026-10-01T17:30:00Z", "generator_commit": "abc1234",
            "tileset": {"name": "protomaps-basemap", "version": "4.15.2", "extensions": []},
            "source": {"kind": "protomaps-build", "timestamp": timestamp, "url": "u", "checksum": "c",
                       "osm_timestamp": "2026-10-01T04:00:00Z"},
            "tile_format": "mvt", "tile_compression": "gzip",
            "release_url": f"https://github.com/exemplo/mapa/releases/download/{build_id}/",
            "attribution": "© colaboradores do OpenStreetMap",
            "resources": {k: v for k, v in self.entry("carcara-recursos.tar.gz").items()
                          if k in ("file", "bytes", "sha256")},
            "base": self.entry("carcara-base.pmtiles"),
            "states": {state: {"name": config.STATES[state],
                               **self.entry(f"carcara-{state}.pmtiles", light=f"carcara-{state}-leve.pmtiles")}
                       for state in states},
        }

    def problems(self, cat=None, published=None, **options):
        return publishing.check(cat or self.cat, published, self.dist, log=self.log.append, **options)


class CheckTest(World):
    def test_a_complete_generation_can_be_published(self):
        self.assertEqual([], self.problems())

    def test_every_file_of_the_catalog_is_listed(self):
        names = [entry["file"] for entry in publishing.files(self.cat)]
        self.assertEqual(27 + 27 + 2, len(names))
        self.assertEqual(len(names), len(set(names)))
        for name in ("carcara-recursos.tar.gz", "carcara-base.pmtiles", "carcara-GO.pmtiles",
                     "carcara-GO-leve.pmtiles"):
            self.assertIn(name, names)

    def test_generation_that_fell_midway_is_not_published(self):
        (self.dist / config.IN_PROGRESS_MARKER).write_text("x")
        self.assertTrue(any("caiu no meio" in p for p in self.problems()))

    def test_partial_generation_is_not_published(self):
        partial = self.catalog_of(["DF", "GO"])
        problems = self.problems(cat=partial)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("parcial", problems[0])
        self.assertIn("25", problems[0])

    def test_missing_file_blocks(self):
        (self.dist / "carcara-GO-leve.pmtiles").unlink()
        self.assertEqual(1, len(self.problems()))
        self.assertIn("carcara-GO-leve.pmtiles", self.problems()[0])

    def test_file_changed_after_the_catalog_blocks(self):
        (self.dist / "carcara-GO.pmtiles").write_bytes(b"x" * (self.cat["states"]["GO"]["bytes"]))
        problems = self.problems()
        self.assertEqual(1, len(problems), problems)
        self.assertIn("sha256", problems[0])

    def test_file_at_the_release_limit_blocks(self):
        with mock.patch.object(config, "MAX_ASSET_BYTES", 30):
            problems = self.problems()
        self.assertTrue(problems)
        self.assertTrue(all("limite" in p for p in problems))

    def test_catalog_of_another_schema_blocks(self):
        self.cat["schema"] = 2
        self.assertTrue(any("schema" in p for p in self.problems()))

    def test_catalog_of_another_tileset_version_blocks(self):
        self.cat["tileset"]["version"] = "5.0.0"
        self.assertTrue(any("5.0.0" in p for p in self.problems()))

    def test_build_id_out_of_format_blocks(self):
        # O build_id vira etiqueta de release, e a limpeza só reconhece o formato AAAA-MM-DD-xxxxxxxx.
        self.cat["build_id"] = "teste"
        self.assertTrue(any("build_id" in p for p in self.problems()))

    def test_drop_against_the_published_catalog_blocks(self):
        published = json.loads(json.dumps(self.cat))
        published["build_id"] = "2026-09-02-aaaaaaaa"
        published["source"]["timestamp"] = "2026-09-02T09:00:00.000Z"
        published["states"]["GO"]["tiles"] = 2000
        problems = self.problems(published=published)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("carcara-GO.pmtiles", problems[0])
        self.assertEqual([], self.problems(published=published, accept_drop=True))
        self.assertTrue(any("--accept-drop" in line for line in self.log))

    def test_state_that_vanished_from_the_new_catalog_is_a_problem(self):
        published = json.loads(json.dumps(self.cat))
        published["build_id"] = "2026-09-02-aaaaaaaa"
        published["source"]["timestamp"] = "2026-09-02T09:00:00.000Z"
        del self.cat["states"]["AC"]
        problems = self.problems(published=published)
        self.assertTrue(any("AC" in p for p in problems), problems)

    def test_older_build_than_the_published_one_blocks(self):
        published = json.loads(json.dumps(self.cat))
        published["build_id"] = "2026-10-20-aaaaaaaa"
        published["source"]["timestamp"] = "2026-10-20T09:00:00.000Z"
        problems = self.problems(published=published)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("mais antigo", problems[0])
        self.assertEqual([], self.problems(published=published, accept_older=True))


class FakeGit:
    def __init__(self, email="12345+alguem@users.noreply.github.com"):
        self.commands = []
        self.email = email
        self.fail = None

    def __call__(self, *args):
        self.commands.append(list(args))
        if args[0] == self.fail:
            return 1, "", f"git {args[0]} recusado"
        if args[:2] == ("config", "user.email"):
            return 0, self.email + "\n", ""
        return 0, "", ""

    def actions(self):
        return [c[0] for c in self.commands]


class PublishGenerationTest(World):
    def setUp(self):
        super().setUp()
        self.gh = FakeGh()
        self.git = FakeGit()
        self.listing = []  # o que o `gh release list` devolve para a limpeza

        gh = self.gh

        def gh_with_list(args):
            if args[1] == "list":
                gh.commands.append(list(args))
                return 0, json.dumps(self.listing), ""
            if args[1] == "delete":
                gh.commands.append(list(args))
                self.listing = [r for r in self.listing if r["tagName"] != args[2]]
                return 0, "", ""
            return gh(args)
        self.call = gh_with_list

    def publish(self, commit=True, push=True, keep=3):
        return publishing.publish_generation(self.cat, self.dist, self.repo, self.call, self.git, commit=commit,
                                             push=push, keep=keep, log=self.log.append)

    def test_release_goes_up_with_every_file_and_is_published(self):
        self.publish()
        release = self.gh.releases[TAG]
        self.assertFalse(release["draft"])
        self.assertEqual(56, len(release["assets"]))

    def test_catalog_and_readme_only_change_after_the_release_is_public(self):
        seen = {}
        original = self.git.__call__

        def spy(*args):
            if args[0] == "add":
                seen["draft_when_committing"] = self.gh.releases[TAG]["draft"]
            return original(*args)
        publishing.publish_generation(self.cat, self.dist, self.repo, self.call, spy, commit=True, push=True, keep=3,
                                      log=self.log.append)
        self.assertFalse(seen["draft_when_committing"])
        self.assertEqual(TAG, json.loads((self.repo / "catalogo.json").read_text(encoding="utf-8"))["build_id"])
        readme = (self.repo / "README.md").read_text(encoding="utf-8")
        self.assertIn("carcara-GO-leve.pmtiles", readme)
        self.assertTrue(readme.startswith("# Projeto"))
        self.assertTrue(readme.endswith("resto\n"))

    def test_commit_has_only_the_catalog_and_the_readme(self):
        self.publish()
        self.assertEqual(["add", "commit", "push"], self.git.actions())
        self.assertEqual(["add", "catalogo.json", "README.md"], self.git.commands[0])
        commit = self.git.commands[1]
        self.assertEqual(["commit", "-m", f"Geração {TAG}", "--", "catalogo.json", "README.md"], commit)

    def test_failed_release_leaves_the_repository_untouched(self):
        self.gh.fail_upload_of.add("carcara-MG.pmtiles")
        with self.assertRaises(publishing.GhError):
            self.publish()
        self.assertFalse((self.repo / "catalogo.json").exists())
        self.assertEqual(README, (self.repo / "README.md").read_text(encoding="utf-8"))
        self.assertEqual([], self.git.commands)

    def test_without_commit_the_files_are_written_and_git_is_not_called(self):
        self.publish(commit=False, push=False)
        self.assertTrue((self.repo / "catalogo.json").exists())
        self.assertEqual([], self.git.commands)

    def test_old_releases_are_pruned_only_after_the_push(self):
        old = ["2026-06-05-aaaaaaaa", "2026-07-04-bbbbbbbb", "2026-08-02-cccccccc"]
        self.listing = [{"tagName": t, "isDraft": False, "publishedAt": f"{t[:10]}T07:40:00Z"} for t in old + [TAG]]
        self.publish()
        deletes = [c[2] for c in self.gh.commands if c[1] == "delete"]
        self.assertEqual(["2026-06-05-aaaaaaaa"], deletes)
        position = [c[1] for c in self.gh.commands].index("delete")
        self.assertEqual("list", self.gh.commands[position - 1][1])
        self.assertIn("push", self.git.actions())

    def test_no_pruning_without_push(self):
        self.listing = [{"tagName": t, "isDraft": False, "publishedAt": "x"} for t in
                        ("2026-06-05-aaaaaaaa", "2026-07-04-bbbbbbbb", "2026-08-02-cccccccc", TAG)]
        self.publish(commit=True, push=False)
        self.assertEqual(["add", "commit"], self.git.actions())  # sem --push, nada é enviado
        self.assertNotIn("delete", [c[1] for c in self.gh.commands])
        self.assertNotIn("list", [c[1] for c in self.gh.commands])

    def test_pruning_failure_is_a_warning_not_a_failure(self):
        self.listing = "isto não é uma lista"
        self.publish()
        self.assertTrue(any("releases antigas não apagadas" in line for line in self.log), self.log)
        self.assertFalse(self.gh.releases[TAG]["draft"])

    def test_git_failure_is_raised_with_what_git_said(self):
        self.git.fail = "push"
        with self.assertRaises(publishing.GitError) as ctx:
            self.publish()
        self.assertIn("push", str(ctx.exception))
        self.assertNotIn("delete", [c[1] for c in self.gh.commands])  # sem push, o catálogo publicado não mudou

    def test_release_notes_credit_the_data(self):
        self.publish()
        create = next(c for c in self.gh.commands if c[1] == "create")
        notes = create[create.index("--notes") + 1]
        self.assertIn("OpenStreetMap", notes)
        self.assertIn("4.15.2", notes)
        self.assertIn(f"Carcará {TAG}", create[create.index("--title") + 1])


class IdentityTest(unittest.TestCase):
    def test_personal_address_blocks_the_commit(self):
        git = FakeGit(email="alguem@exemplo.com")
        self.assertIsNotNone(publishing.commit_identity_problem(git))

    def test_anonymous_address_passes(self):
        self.assertIsNone(publishing.commit_identity_problem(FakeGit()))


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generate  # noqa: E402
from carcara import (catalog, config, extraction, packs, pmtiles_tool, regions, resources, run_record,  # noqa: E402
                     sources, validation)

BUILD = {"key": "20261001.pmtiles", "url": "https://exemplo.invalid/20261001.pmtiles", "size": 1,
         "b3sum": "2b7e7669" + "0" * 56, "uploaded": "2026-10-01T08:53:09.033Z", "version": "4.15.2"}


class StatesOptionTest(unittest.TestCase):
    def test_default_is_every_state(self):
        self.assertEqual(sorted(config.STATES), generate.parse_states(None))

    def test_list_is_cleaned_and_sorted(self):
        self.assertEqual(["DF", "GO"], generate.parse_states(" go, df ,GO"))

    def test_unknown_state_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            generate.parse_states("DF,XX")
        self.assertIn("XX", str(ctx.exception))

    def test_empty_list_is_refused(self):
        with self.assertRaises(ValueError):
            generate.parse_states(" , ")


class BuildIdTest(unittest.TestCase):
    def test_date_of_the_build_and_the_start_of_its_checksum(self):
        self.assertEqual("2026-10-01-2b7e7669", sources.build_id(BUILD))

    def test_malformed_build_is_refused(self):
        with self.assertRaises(ValueError):
            sources.build_id(dict(BUILD, uploaded="ontem"))
        with self.assertRaises(ValueError):
            sources.build_id(dict(BUILD, b3sum="XYZ"))


class RunTest(unittest.TestCase):
    """A ordem das etapas, com tudo o que toca a rede ou a ferramenta no lugar de dublês."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name)
        self.order = []

        def step(name, result=None):
            def call(*args, **kwargs):
                self.order.append(name)
                return result
            return call

        for target, attribute, result in [
            (pmtiles_tool, "require", None),
            (sources, "ibge_mesh", self.data / "malha.json"),
            (regions, "write_regions", {"DF": Path("DF.geojson"), "brasil": Path("brasil.geojson")}),
            (sources, "latest_build", BUILD),
            (packs, "generate", {"DF": {"bytes": 10, "transfer_bytes": 11, "light": {"bytes": 3}},
                                 "base": {"file": "carcara-base.pmtiles", "bytes": 5, "transfer_bytes": 6,
                                          "light": None}}),
            (resources, "build", {"file": "carcara-recursos.tar.gz", "bytes": 7, "sha256": "ab",
                                  "path": self.data / "dist" / "carcara-recursos.tar.gz"}),
            (regions, "state_polygons", {"DF": "polígono"}),
            (validation, "validate", []),
            (extraction, "metadata", {"planetiler:osm:osmosisreplicationtime": "2026-10-01T04:00:00Z"}),
            (catalog, "build_catalog", {"schema": 1, "build_id": "2026-10-01-2b7e7669"}),
        ]:
            mock.patch.object(target, attribute, side_effect=step(f"{target.__name__.split('.')[-1]}.{attribute}",
                                                                  result)).start()
        for name, value in [("DATA", self.data), ("DIST", self.data / "dist"), ("REGIONS", self.data / "regioes"),
                            ("REPO", self.data / "repo")]:
            mock.patch.object(config, name, value).start()
        mock.patch.object(generate, "check_disk_space").start()

    def tearDown(self):
        mock.patch.stopall()
        self._tmp.cleanup()

    def run_generation(self, states=("DF",), accept_drop=False):
        recorder = run_record.RunRecorder(self.data, interval=3600)
        try:
            return generate.run(list(states), recorder, light=True, accept_drop=accept_drop)
        finally:
            recorder.save(self.data / "dist" / "geracao.json", "teste")

    def test_tool_is_checked_before_anything_is_downloaded(self):
        self.run_generation()
        self.assertEqual("pmtiles_tool.require", self.order[0])
        self.assertEqual(["pmtiles_tool.require", "sources.ibge_mesh", "regions.write_regions", "sources.latest_build",
                          "packs.generate", "resources.build", "regions.state_polygons", "validation.validate",
                          "extraction.metadata", "catalog.build_catalog"], self.order)

    def test_summary_says_what_was_made(self):
        summary = self.run_generation()
        self.assertIn("2026-10-01-2b7e7669", summary)
        self.assertIn("1 estado", summary)

    def test_packs_are_asked_for_the_chosen_states_with_the_chosen_build(self):
        self.run_generation(states=("DF",))
        args, kwargs = packs.generate.call_args
        self.assertEqual(BUILD, args[0])
        self.assertEqual(["DF"], args[2])
        self.assertEqual(self.data / "dist", args[3])
        self.assertTrue(kwargs["light"])

    def test_generation_record_has_one_entry_per_stage(self):
        self.run_generation()
        record = json.loads((self.data / "dist" / "geracao.json").read_text(encoding="utf-8"))
        self.assertEqual(["prepare", "packs", "resources", "validate", "catalog"],
                         [s["stage"] for s in record["stages"]])
        self.assertTrue(all(s["status"] == "ok" for s in record["stages"]))

    def test_catalog_is_written_next_to_the_packs_with_the_data_date(self):
        self.run_generation()
        written = json.loads((self.data / "dist" / "catalogo.json").read_text(encoding="utf-8"))
        self.assertEqual("2026-10-01-2b7e7669", written["build_id"])
        self.assertEqual("2026-10-01T04:00:00Z", catalog.build_catalog.call_args.kwargs["osm_timestamp"])
        self.assertEqual(self.data / "dist" / "carcara-base.pmtiles", extraction.metadata.call_args.args[0])

    def test_no_catalog_when_the_validation_bars(self):
        validation.validate.side_effect = None
        validation.validate.return_value = ["trava tamanho: grande"]
        with self.assertRaises(generate.ValidationFailed):
            self.run_generation()
        self.assertFalse((self.data / "dist" / "catalogo.json").exists())

    def test_validation_gets_the_generation_and_the_options(self):
        self.run_generation(accept_drop=True)
        kwargs = validation.validate.call_args.kwargs
        self.assertEqual(self.data / "dist", kwargs["dist"])
        self.assertEqual(["DF"], kwargs["states"])
        self.assertEqual(BUILD, kwargs["build"])
        self.assertEqual({"DF": "polígono"}, kwargs["polygons"])
        self.assertTrue(kwargs["light"])
        self.assertTrue(kwargs["accept_drop"])
        self.assertIsNone(kwargs["published"])  # não há catalogo.json na raiz do repositório

    def test_published_catalog_at_the_repository_root_is_what_the_drop_check_compares_with(self):
        (self.data / "repo").mkdir()
        (self.data / "repo" / "catalogo.json").write_text('{"build_id": "2026-09-02-aaaaaaaa", "states": {}}',
                                                           encoding="utf-8")
        self.run_generation()
        self.assertEqual("2026-09-02-aaaaaaaa", validation.validate.call_args.kwargs["published"]["build_id"])

    def test_published_catalog_that_does_not_parse_stops_the_generation(self):
        # Sem conseguir ler o catálogo publicado, a trava de queda não teria com o que comparar: melhor parar.
        (self.data / "repo").mkdir()
        (self.data / "repo" / "catalogo.json").write_text("<html>", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.run_generation()

    def test_problems_stop_the_generation_with_the_list(self):
        validation.validate.side_effect = None
        validation.validate.return_value = ["trava divisa: DF e GO: diferente", "trava tamanho: grande"]
        with self.assertRaises(generate.ValidationFailed) as ctx:
            self.run_generation()
        self.assertEqual(2, len(ctx.exception.problems))
        record = json.loads((self.data / "dist" / "geracao.json").read_text(encoding="utf-8"))
        self.assertEqual("failed", record["stages"][-1]["status"])

    def test_partial_generation_is_marked_as_such(self):
        summary = self.run_generation(states=("DF",))
        self.assertIn("parcial", summary)
        record = json.loads((self.data / "dist" / "geracao.json").read_text(encoding="utf-8"))
        self.assertTrue(record["partial"])


class MarkerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name)
        for name, value in [("DATA", self.data), ("DIST", self.data / "dist")]:
            mock.patch.object(config, name, value).start()

    def tearDown(self):
        mock.patch.stopall()
        self._tmp.cleanup()

    def test_marker_is_removed_when_the_generation_finishes(self):
        with mock.patch.object(generate, "run", return_value="geração de teste"):
            self.assertEqual(0, generate.main(["--states", "DF"]))
        self.assertFalse((self.data / "dist" / config.IN_PROGRESS_MARKER).exists())
        record = json.loads((self.data / "dist" / "geracao.json").read_text(encoding="utf-8"))
        self.assertEqual("ok", record["result"])

    def test_marker_stays_when_the_generation_falls(self):
        # Quem publica olha esta marca: se ela existe, a geração caiu no meio e nada deve ser publicado.
        with mock.patch.object(generate, "run", side_effect=RuntimeError("conexão caiu")):
            with self.assertRaises(RuntimeError):
                generate.main(["--states", "DF"])
        self.assertTrue((self.data / "dist" / config.IN_PROGRESS_MARKER).exists())
        record = json.loads((self.data / "dist" / "geracao.json").read_text(encoding="utf-8"))
        self.assertIn("conexão caiu", record["result"])

    def test_failed_validation_ends_with_an_error_code_and_keeps_the_marker(self):
        failure = generate.ValidationFailed(["trava tamanho: carcara-MG.pmtiles tem 2.10 GB"])
        with mock.patch.object(generate, "run", side_effect=failure):
            self.assertEqual(1, generate.main(["--states", "DF"]))
        self.assertTrue((self.data / "dist" / config.IN_PROGRESS_MARKER).exists())
        record = json.loads((self.data / "dist" / "geracao.json").read_text(encoding="utf-8"))
        self.assertEqual("failed: validation", record["result"])
        self.assertEqual(["trava tamanho: carcara-MG.pmtiles tem 2.10 GB"], record["problems"])

    def test_accept_drop_is_passed_on(self):
        with mock.patch.object(generate, "run", return_value="geração de teste") as run:
            generate.main(["--states", "DF", "--accept-drop"])
        self.assertTrue(run.call_args.kwargs["accept_drop"])

    def test_unknown_state_ends_with_an_error_code_and_no_marker(self):
        self.assertEqual(2, generate.main(["--states", "XX"]))
        self.assertFalse((self.data / "dist" / config.IN_PROGRESS_MARKER).exists())


class DiskSpaceTest(unittest.TestCase):
    def test_too_little_space_stops_before_downloading(self):
        with self.assertRaises(RuntimeError) as ctx:
            generate.check_disk_space(Path("."), minimum=20_000_000_000, free=5_000_000_000)
        self.assertIn("5.0 GB", str(ctx.exception))

    def test_enough_space_passes(self):
        generate.check_disk_space(Path("."), minimum=20_000_000_000, free=25_000_000_000)


if __name__ == "__main__":
    unittest.main()

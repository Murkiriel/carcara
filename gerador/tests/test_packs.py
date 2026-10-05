import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, extraction, packs  # noqa: E402

BUILD = {"key": "20261001.pmtiles", "url": "https://exemplo.invalid/20261001.pmtiles", "size": 138_000_000_000,
         "b3sum": "2b7e7669" + "0" * 56, "uploaded": "2026-10-01T08:53:09.033Z", "version": "4.15.2"}
OTHER_BUILD = dict(BUILD, key="20261030.pmtiles", url="https://exemplo.invalid/20261030.pmtiles",
                   b3sum="aaaaaaaa" + "0" * 56, uploaded="2026-10-30T09:00:00.000Z")


def header(maxzoom: int, tiles: int = 100) -> extraction.Header:
    return extraction.Header(tile_type="mvt", tile_compression="gzip", minzoom=0, maxzoom=maxzoom,
                             bounds=(-48.3, -16.1, -47.2, -15.4), addressed_tiles=tiles, tile_entries=tiles - 1,
                             tile_contents=tiles - 2, clustered=True)


class NamesTest(unittest.TestCase):
    def test_file_names(self):
        self.assertEqual("carcara-GO.pmtiles", packs.state_file("GO"))
        self.assertEqual("carcara-GO-leve.pmtiles", packs.light_file("GO"))
        self.assertEqual("carcara-base.pmtiles", packs.BASE_FILE)


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self._tmp.name) / "dist"
        self.regions = {name: Path(f"{name}.geojson") for name in list(config.STATES) + ["brasil"]}
        self.calls = []

        def fake_extract(source, dest, maxzoom, region=None):
            self.calls.append({"source": source, "dest": dest.name, "maxzoom": maxzoom, "region": region})
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(f"{dest.name} de {source}".encode())
            return extraction.Estimate(region_tiles=100, tile_entries=99, archive_bytes=1_000_000,
                                       archive_resolution=1_000_000, transfer_bytes=1_100_000, requests=7)

        def fake_set_attribution(path, text):
            path.write_bytes(path.read_bytes() + b" + credito")

        self._patches = [mock.patch.object(extraction, "extract", side_effect=fake_extract),
                         mock.patch.object(extraction, "set_attribution", side_effect=fake_set_attribution),
                         mock.patch.object(extraction, "verify"),
                         mock.patch.object(extraction, "header", side_effect=lambda path: header(
                             13 if "-leve" in path.name else 9 if "base" in path.name else 15))]
        for p in self._patches:
            p.start()

    def tearDown(self):
        mock.patch.stopall()
        self._tmp.cleanup()

    def generate(self, states=("DF", "GO"), build=BUILD, light=True):
        return packs.generate(build, self.regions, list(states), self.dist, light=light)

    def test_each_state_is_cut_from_the_build_by_its_region_up_to_zoom_15(self):
        self.generate()
        call = next(c for c in self.calls if c["dest"] == "carcara-GO.pmtiles")
        self.assertEqual({"source": BUILD["url"], "dest": "carcara-GO.pmtiles", "maxzoom": 15,
                          "region": Path("GO.geojson")}, call)

    def test_base_is_the_country_up_to_zoom_9(self):
        self.generate()
        call = next(c for c in self.calls if c["dest"] == "carcara-base.pmtiles")
        self.assertEqual({"source": BUILD["url"], "dest": "carcara-base.pmtiles", "maxzoom": 9,
                          "region": Path("brasil.geojson")}, call)

    def test_light_pack_comes_from_the_local_full_file_not_from_the_build(self):
        self.generate()
        call = next(c for c in self.calls if c["dest"] == "carcara-GO-leve.pmtiles")
        self.assertEqual(str(self.dist / "carcara-GO.pmtiles"), call["source"])
        self.assertEqual(13, call["maxzoom"])
        self.assertIsNone(call["region"])
        self.assertEqual(3, sum(1 for c in self.calls if c["source"] == BUILD["url"]))  # DF, GO e a base

    def test_without_light_packs_only_the_full_ones_are_made(self):
        result = self.generate(light=False)
        self.assertFalse(any("-leve" in c["dest"] for c in self.calls))
        self.assertIsNone(result["DF"]["light"])
        self.assertEqual(["carcara-DF.pmtiles", "carcara-GO.pmtiles", "carcara-base.pmtiles"],
                         sorted(p.name for p in self.dist.glob("*.pmtiles")))

    def test_every_file_is_verified(self):
        self.generate(states=("DF",))
        verified = sorted(call.args[0].name for call in extraction.verify.call_args_list)
        self.assertEqual(["carcara-DF-leve.pmtiles", "carcara-DF.pmtiles", "carcara-base.pmtiles"], verified)

    def test_every_file_gets_the_whole_credit_before_it_is_measured(self):
        # Decisão do dono em 2026-10-05: o crédito do ESA WorldCover também dentro de cada arquivo.
        result = self.generate(states=("DF",))
        credited = extraction.set_attribution.call_args_list
        self.assertEqual(["carcara-DF-leve.pmtiles", "carcara-DF.pmtiles", "carcara-base.pmtiles"],
                         sorted(call.args[0].name for call in credited))
        self.assertTrue(all(call.args[1] == config.EMBEDDED_ATTRIBUTION for call in credited))
        content = (self.dist / "carcara-DF.pmtiles").read_bytes()
        self.assertTrue(content.endswith(b" + credito"))
        self.assertEqual(len(content), result["DF"]["bytes"])

    def test_pack_record_has_what_the_catalog_needs(self):
        result = self.generate(states=("DF",))
        pack = result["DF"]
        content = (self.dist / "carcara-DF.pmtiles").read_bytes()
        self.assertEqual("carcara-DF.pmtiles", pack["file"])
        self.assertEqual(len(content), pack["bytes"])
        self.assertRegex(pack["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(100, pack["tiles"])
        self.assertEqual((0, 15), (pack["minzoom"], pack["maxzoom"]))
        self.assertEqual([-48.3, -16.1, -47.2, -15.4], pack["bounds"])
        self.assertEqual(1_100_000, pack["transfer_bytes"])
        self.assertEqual("carcara-DF-leve.pmtiles", pack["light"]["file"])
        self.assertEqual(13, pack["light"]["maxzoom"])
        self.assertEqual(["DF", "base"], sorted(result))

    def test_manifest_is_saved_with_the_build(self):
        self.generate(states=("DF",))
        manifest = json.loads((self.dist / "pacotes.json").read_text(encoding="utf-8"))
        self.assertEqual(BUILD["key"], manifest["build"]["key"])
        self.assertEqual(["DF", "base"], sorted(manifest["packs"]))

    def test_second_run_of_the_same_build_reuses_what_is_done(self):
        self.generate()
        self.calls.clear()
        result = self.generate(states=("DF", "GO", "SE"))
        self.assertEqual(["carcara-SE-leve.pmtiles", "carcara-SE.pmtiles"], sorted(c["dest"] for c in self.calls))
        self.assertEqual(["DF", "GO", "SE", "base"], sorted(result))

    def test_file_changed_since_the_manifest_is_cut_again(self):
        self.generate(states=("DF",))
        (self.dist / "carcara-DF.pmtiles").write_bytes(b"encolheu")
        self.calls.clear()
        self.generate(states=("DF",))
        self.assertIn("carcara-DF.pmtiles", [c["dest"] for c in self.calls])

    def test_another_build_starts_over(self):
        self.generate()
        self.calls.clear()
        result = self.generate(states=("DF",), build=OTHER_BUILD)
        self.assertEqual(["carcara-DF-leve.pmtiles", "carcara-DF.pmtiles", "carcara-base.pmtiles"],
                         sorted(c["dest"] for c in self.calls))
        # Nada da geração anterior fica misturado com a nova.
        self.assertEqual(["carcara-DF-leve.pmtiles", "carcara-DF.pmtiles", "carcara-base.pmtiles"],
                         sorted(p.name for p in self.dist.glob("*.pmtiles")))
        self.assertEqual(["DF", "base"], sorted(result))

    def test_failure_keeps_what_was_already_done(self):
        original = extraction.extract.side_effect

        def failing(source, dest, maxzoom, region=None):
            if dest.name == "carcara-GO.pmtiles":
                raise RuntimeError("conexão caiu")
            return original(source, dest, maxzoom, region)

        extraction.extract.side_effect = failing
        with self.assertRaises(RuntimeError):
            self.generate()
        manifest = json.loads((self.dist / "pacotes.json").read_text(encoding="utf-8"))
        self.assertIn("DF", manifest["packs"])
        self.assertNotIn("GO", manifest["packs"])

    def test_unknown_state_is_refused_before_anything_is_cut(self):
        with self.assertRaises(ValueError):
            self.generate(states=("DF", "XX"))
        self.assertEqual([], self.calls)

    def test_wrong_header_is_refused(self):
        extraction.header.side_effect = lambda path: header(14)  # recorte que não chegou ao zoom pedido
        with self.assertRaises(RuntimeError) as ctx:
            self.generate(states=("DF",))
        self.assertIn("zoom", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

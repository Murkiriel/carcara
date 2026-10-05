import json
import re
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import catalog, config, mvt, validation  # noqa: E402

from shapely.geometry import box  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
BUILD = {"key": "20261001.pmtiles", "url": "https://build.protomaps.com/20261001.pmtiles", "size": 138_507_309_367,
         "b3sum": "2b7e7669" + "0" * 56, "uploaded": "2026-10-01T08:53:09.033Z", "version": "4.15.2"}
POLYGONS = {"DF": box(-48.2857, -16.0501, -47.3086, -15.5001), "GO": box(-53.2485, -19.4981, -45.9072, -12.3954)}
RESOURCES = {"file": "carcara-recursos.tar.gz", "bytes": 6_155_919, "sha256": "1f" * 32, "path": Path("x"),
             "revision": "028c18f7", "glyph_files": 768, "sprite_files": 20}


def pack(file, size, tiles, maxzoom, bounds, light=None):
    return {"file": file, "bytes": size, "sha256": "ab" * 32, "tiles": tiles, "tile_entries": tiles - 1,
            "minzoom": 0, "maxzoom": maxzoom, "bounds": bounds, "transfer_bytes": size + 5, "requests": 9,
            "seconds": 1.5, "light": light}


def generation(light=True):
    df_bounds, go_bounds = [-48.335697, -16.0999999, -47.2585026, -15.4518], [-53.2985, -19.5481, -45.8572, -12.3454]
    df_light = pack("carcara-DF-leve.pmtiles", 7_082_704, 576, 13, df_bounds) if light else None
    go_light = pack("carcara-GO-leve.pmtiles", 50_233_439, 22_896, 13, go_bounds) if light else None
    for record in (df_light, go_light):
        if record:
            del record["light"]
    return {"GO": pack("carcara-GO.pmtiles", 182_443_237, 355_106, 15, go_bounds, go_light),
            "DF": pack("carcara-DF.pmtiles", 47_992_685, 7_868, 15, df_bounds, df_light),
            "base": pack("carcara-base.pmtiles", 44_282_829, 2_295, 9, [-74.04, -33.80, -29.25, 5.32])}


def build(light=True):
    return catalog.build_catalog(BUILD, generation(light), RESOURCES, POLYGONS,
                                 osm_timestamp="2026-10-01T04:00:00Z", built_at="2026-10-01T17:30:00Z",
                                 generator_commit="abc1234")


class FormatTest(unittest.TestCase):
    def test_top_level_keys(self):
        self.assertEqual(["schema", "build_id", "built_at", "generator_commit", "tileset", "source", "tile_format",
                          "tile_compression", "release_url", "attribution", "resources", "base", "states"],
                         list(build()))

    def test_identity_of_the_generation(self):
        cat = build()
        self.assertEqual(1, cat["schema"])
        self.assertEqual("2026-10-01-2b7e7669", cat["build_id"])
        self.assertEqual("2026-10-01T17:30:00Z", cat["built_at"])
        self.assertEqual("abc1234", cat["generator_commit"])

    def test_tileset_says_which_schema_the_styles_must_know(self):
        self.assertEqual({"name": "protomaps-basemap", "version": "4.15.2", "extensions": []}, build()["tileset"])

    def test_source_says_where_the_tiles_came_from(self):
        self.assertEqual({"kind": "protomaps-build", "timestamp": "2026-10-01T08:53:09.033Z",
                          "url": "https://build.protomaps.com/20261001.pmtiles", "checksum": BUILD["b3sum"],
                          "osm_timestamp": "2026-10-01T04:00:00Z"}, build()["source"])

    def test_tiles_are_gzipped_vector_tiles(self):
        cat = build()
        self.assertEqual(("mvt", "gzip"), (cat["tile_format"], cat["tile_compression"]))

    def test_release_url_is_the_one_of_this_generation(self):
        cat = build()
        self.assertTrue(cat["release_url"].endswith("/releases/download/2026-10-01-2b7e7669/"), cat["release_url"])
        self.assertTrue(cat["release_url"].startswith("https://github.com/"))

    def test_attribution_credits_openstreetmap(self):
        self.assertIn("OpenStreetMap", build()["attribution"])

    def test_attribution_credits_the_land_cover_source(self):
        # A camada landcover (zooms 0 a 7) vem do ESA WorldCover, sob CC BY 4.0, que pede esta frase em mapa publicado.
        attribution = build()["attribution"]
        self.assertIn("© ESA WorldCover project 2020 / Contains modified Copernicus Sentinel data (2020) processed by "
                      "ESA WorldCover consortium", attribution)
        self.assertIn("CC BY 4.0", attribution)

    def test_resources_entry(self):
        self.assertEqual({"file": "carcara-recursos.tar.gz", "bytes": 6_155_919, "sha256": "1f" * 32},
                         build()["resources"])

    def test_built_at_defaults_to_now_in_utc(self):
        cat = catalog.build_catalog(BUILD, generation(), RESOURCES, POLYGONS, osm_timestamp="x", generator_commit="a")
        self.assertRegex(cat["built_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class PackEntryTest(unittest.TestCase):
    def test_state_entry(self):
        go = build()["states"]["GO"]
        self.assertEqual(["name", "file", "bytes", "sha256", "tiles", "minzoom", "maxzoom", "bbox", "bbox_tiles",
                          "light"], list(go))
        self.assertEqual("Goiás", go["name"])
        self.assertEqual(("carcara-GO.pmtiles", 182_443_237, 355_106, 0, 15),
                         (go["file"], go["bytes"], go["tiles"], go["minzoom"], go["maxzoom"]))

    def test_states_come_in_order(self):
        self.assertEqual(["DF", "GO"], list(build()["states"]))

    def test_light_entry(self):
        light = build()["states"]["DF"]["light"]
        self.assertEqual({"file": "carcara-DF-leve.pmtiles", "bytes": 7_082_704, "sha256": "ab" * 32, "tiles": 576,
                          "minzoom": 0, "maxzoom": 13}, light)

    def test_without_light_packs_the_key_is_absent(self):
        # `light` é opcional: quem não conhece a chave não quebra, e uma geração sem leves não a escreve.
        self.assertNotIn("light", build(light=False)["states"]["DF"])

    def test_base_entry_has_no_name_and_no_light(self):
        base = build()["base"]
        self.assertEqual(["file", "bytes", "sha256", "tiles", "minzoom", "maxzoom", "bbox", "bbox_tiles"], list(base))
        self.assertEqual(9, base["maxzoom"])

    def test_what_is_internal_to_the_generator_stays_out(self):
        text = json.dumps(build())
        for internal in ("transfer_bytes", "requests", "seconds", "tile_entries", "bounds\"", "path", "revision"):
            self.assertNotIn(internal, text)

    def test_bbox_is_the_state_polygon_latitude_first_rounded_outwards(self):
        self.assertEqual([-16.06, -48.29, -15.5, -47.3], build()["states"]["DF"]["bbox"])

    def test_base_bbox_is_the_whole_of_what_the_mesh_has(self):
        self.assertEqual([-19.5, -53.25, -12.39, -45.9], build()["base"]["bbox"])

    def test_bbox_tiles_is_the_tile_aligned_area_and_covers_the_bbox(self):
        entry = build()["states"]["DF"]
        lat_min, lon_min, lat_max, lon_max = entry["bbox_tiles"]
        bbox = entry["bbox"]
        self.assertTrue(lat_min <= bbox[0] and lon_min <= bbox[1] and lat_max >= bbox[2] and lon_max >= bbox[3])
        # Cobre a área do arquivo (o polígono com a margem) e não passa dela mais que um tile do zoom 15 (~0,011°).
        self.assertLessEqual(lon_min, -48.335697)
        self.assertGreater(lon_min, -48.335697 - 0.012)
        self.assertGreaterEqual(lat_max, -15.4518)
        self.assertLess(lat_max, -15.4518 + 0.012)


class TileBoundsTest(unittest.TestCase):
    def test_bounds_of_a_tile_contain_the_point_it_was_asked_for(self):
        x, y = mvt.tile_at(-15.7942, -47.8825, 15)
        west, south, east, north = mvt.tile_bounds(15, x, y)
        self.assertTrue(west <= -47.8825 <= east and south <= -15.7942 <= north)
        self.assertAlmostEqual(360 / 2 ** 15, east - west, places=9)

    def test_world_tile(self):
        west, south, east, north = mvt.tile_bounds(0, 0, 0)
        self.assertEqual((-180.0, 180.0), (west, east))
        self.assertAlmostEqual(85.0511, north, places=3)
        self.assertAlmostEqual(-85.0511, south, places=3)


class SaveTest(unittest.TestCase):
    def test_saved_as_readable_utf8_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "catalogo.json"
            catalog.save(build(), dest)
            text = dest.read_text(encoding="utf-8")
            self.assertIn("Goiás", text)          # acento como é, não á
            self.assertTrue(text.endswith("}\n"))
            self.assertEqual(build(), json.loads(text))


class DropCheckContractTest(unittest.TestCase):
    """O catálogo publicado é o que a trava de queda compara com a geração seguinte."""

    def test_the_same_generation_shows_no_drop(self):
        log = []
        self.assertEqual([], validation.check_drop(generation(), build(), False, log.append))

    def test_a_smaller_generation_shows_the_drop_in_full_and_light_packs(self):
        published = build()
        published["states"]["GO"]["tiles"] = 400_000
        published["states"]["GO"]["light"]["bytes"] = 60_000_000
        problems = validation.check_drop(generation(), published, False, lambda line: None)
        self.assertEqual(2, len(problems), problems)
        self.assertTrue(any("carcara-GO.pmtiles" in p and "tiles" in p for p in problems))
        self.assertTrue(any("carcara-GO-leve.pmtiles" in p and "bytes" in p for p in problems))


class DownloadsTableTest(unittest.TestCase):
    def table(self, light=True):
        return catalog.downloads_table(build(light))

    def test_one_row_for_the_base_and_one_per_state(self):
        rows = [line for line in self.table().splitlines() if line.startswith("| ") and "carcara-" in line]
        self.assertEqual(3, len(rows))
        self.assertIn("carcara-base.pmtiles", rows[0])

    def test_each_file_links_to_the_release_of_this_generation(self):
        table = self.table()
        url = build()["release_url"]
        for name in ("carcara-base.pmtiles", "carcara-GO.pmtiles", "carcara-GO-leve.pmtiles",
                     "carcara-recursos.tar.gz"):
            self.assertIn(f"]({url}{name})", table)

    def test_sizes_are_written_for_people(self):
        table = self.table()
        self.assertIn("182,4 MB", table)
        self.assertIn("50,2 MB", table)

    def test_states_are_ordered_by_name_ignoring_accents(self):
        cat = build()
        cat["states"] = {state: dict(cat["states"]["DF"], name=config.STATES[state]) for state in config.STATES}
        rows = [line.split("|")[1].strip() for line in catalog.downloads_table(cat).splitlines()
                if line.startswith("| ") and "carcara-" in line and "carcara-base" not in line]
        strip = lambda n: unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()  # noqa: E731
        self.assertEqual(sorted(rows, key=strip), rows)
        self.assertLess(rows.index("Pará (PA)"), rows.index("Paraíba (PB)"))

    def test_heading_says_which_generation_and_which_data(self):
        table = self.table()
        self.assertIn("2026-10-01-2b7e7669", table)
        self.assertIn("4.15.2", table)
        self.assertIn("2026-10-01", table)

    def test_without_light_packs_the_column_is_empty_not_broken(self):
        table = self.table(light=False)
        self.assertNotIn("-leve", table)
        widths = {line.count("|") for line in table.splitlines() if line.startswith("|")}
        self.assertEqual(1, len(widths), "toda linha da tabela tem o mesmo número de colunas")


class ReadmeTest(unittest.TestCase):
    def test_only_what_is_between_the_markers_changes(self):
        text = f"antes\n{catalog.START_MARKER}\nvelho\n{catalog.END_MARKER}\ndepois\n"
        self.assertEqual(f"antes\n{catalog.START_MARKER}\nnovo\n{catalog.END_MARKER}\ndepois\n",
                         catalog.update_readme(text, "novo"))

    def test_readme_without_markers_is_an_error(self):
        with self.assertRaises(ValueError):
            catalog.update_readme("sem marcadores", "novo")

    def test_the_repository_readme_has_the_markers(self):
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertLess(text.index(catalog.START_MARKER), text.index(catalog.END_MARKER))


class DocumentationTest(unittest.TestCase):
    def test_every_key_of_the_catalog_is_described_in_the_architecture_document(self):
        text = (REPO / "docs" / "ARQUITETURA.md").read_text(encoding="utf-8")
        block = text[text.index("## `catalogo.json`"):text.index("## Releases")]
        cat = build()
        keys = set(cat) | set(cat["tileset"]) | set(cat["source"]) | set(cat["states"]["DF"]) | set(cat["resources"])
        missing = sorted(key for key in keys if not re.search(rf"(^|[\s,]){re.escape(key)}([\s,]|$)", block,
                                                              flags=re.MULTILINE))
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()

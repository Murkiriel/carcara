import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, extraction, mvt, packs, regions, resources, validation  # noqa: E402
from tests import mvt_builder  # noqa: E402

from shapely.geometry import Point, box  # noqa: E402

BUILD = {"key": "20261001.pmtiles", "url": "https://exemplo.invalid/20261001.pmtiles", "size": 1,
         "b3sum": "2b7e7669" + "0" * 56, "uploaded": "2026-10-01T08:53:09.033Z", "version": "4.15.2"}

DF = box(-48.29, -16.05, -47.31, -15.50)
GO = box(-53.25, -19.50, -45.91, -12.40).difference(DF)   # Goiás em volta do Distrito Federal
SP = box(-53.11, -25.31, -44.16, -19.78)                  # não encosta em nenhum dos dois
POLYGONS = {"DF": DF, "GO": GO, "SP": SP}
GOOD_TILE = mvt_builder.tile({"roads": 5, "places": 2, "earth": 1})


def png(width: int, height: int) -> bytes:
    """Só o começo de um PNG: a assinatura e o tamanho da imagem, que é o que a validação lê."""
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + b"\x08\x06"


def sprite_index(names) -> bytes:
    return json.dumps({name: {"x": 0, "y": 0, "width": 10, "height": 10, "pixelRatio": 1} for name in names}).encode()


def resource_files() -> dict:
    files = {name: b"x" for name in resources.required()}
    for flavor in resources.SPRITE_FLAVORS:
        icons = validation.required_icons(flavor)
        for density in ("", "@2x"):
            files[f"{resources.SPRITES_FOLDER}{flavor}{density}.json"] = sprite_index(icons)
            files[f"{resources.SPRITES_FOLDER}{flavor}{density}.png"] = png(64, 64)
    files[resources.ICONS_LICENCE] = b"MIT"
    files[resources.README] = b"origem"
    return files


class WorldTest(unittest.TestCase):
    """Uma geração de mentira (DF, GO e a base), com a ferramenta no lugar de dublês, para ver cada trava barrar."""

    states = ["DF", "GO"]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dist = Path(self._tmp.name)
        self.tiles = {}       # {(arquivo, z, x, y): bytes} que fogem do tile bom padrão; None = tile ausente
        self.headers = {}     # {arquivo: campos do cabeçalho trocados}
        self.versions = {}    # {arquivo: versão nos metadados}
        self.broken = set()   # arquivos que o verify recusa
        self.log = []
        self.generated = {state: self.pack(packs.state_file(state), packs.light_file(state)) for state in self.states}
        self.generated["base"] = self.pack(packs.BASE_FILE, None)
        resources.write_archive(resource_files(), self.dist / resources.FILE_NAME)
        archive = self.dist / resources.FILE_NAME
        self.resources_pack = {"file": resources.FILE_NAME, "bytes": archive.stat().st_size, "path": archive}

        def verify(path):
            if path.name in self.broken:
                raise RuntimeError(f"pmtiles verify recusou {path.name}")

        def header(path):
            maxzoom = 13 if "-leve" in path.name else 9 if "base" in path.name else 15
            fields = dict(tile_type="mvt", tile_compression="gzip", minzoom=0, maxzoom=maxzoom,
                          bounds=(-75.0, -35.0, -28.0, 6.0), addressed_tiles=1000, tile_entries=990,
                          tile_contents=980, clustered=True)
            fields.update(self.headers.get(path.name, {}))
            return extraction.Header(**fields)

        for target, attribute, fake in [
            (extraction, "verify", verify), (extraction, "header", header),
            (extraction, "metadata", lambda path: {"version": self.versions.get(path.name, "4.15.2")}),
            (extraction, "read_tile", lambda path, z, x, y: self.tiles.get((path.name, z, x, y), GOOD_TILE)),
        ]:
            mock.patch.object(target, attribute, side_effect=fake).start()

    def tearDown(self):
        mock.patch.stopall()
        self._tmp.cleanup()

    def pack(self, file_name, light_name, tiles=1000):
        (self.dist / file_name).write_bytes(b"t" * 500)
        record = {"file": file_name, "bytes": 500, "sha256": "ab" * 32, "tiles": tiles, "tile_entries": 990,
                  "minzoom": 0, "maxzoom": 15, "bounds": [-75.0, -35.0, -28.0, 6.0], "light": None}
        if light_name:
            (self.dist / light_name).write_bytes(b"l" * 100)
            record["light"] = {"file": light_name, "bytes": 100, "sha256": "cd" * 32, "tiles": 300,
                               "tile_entries": 290, "minzoom": 0, "maxzoom": 13, "bounds": record["bounds"]}
        return record

    def problems(self, **options):
        arguments = dict(dist=self.dist, generated=self.generated, resources_pack=self.resources_pack, build=BUILD,
                         polygons=POLYGONS, states=self.states, light=True, log=self.log.append)
        arguments.update(options)
        return validation.validate(**arguments)

    def capital_tile(self, state, zoom):
        _, lat, lon = validation.CAPITALS[state]
        return (zoom, *mvt.tile_at(lat, lon, zoom))

    def assertOneProblem(self, problems, *fragments):
        self.assertEqual(1, len(problems), problems)
        for fragment in fragments:
            self.assertIn(fragment, problems[0])


class GoodGenerationTest(WorldTest):
    def test_a_good_generation_has_no_problems(self):
        self.assertEqual([], self.problems())

    def test_log_says_which_checks_ran(self):
        self.problems()
        text = "\n".join(self.log)
        for check in ("estrutura", "cabeçalho", "conteúdo", "divisa", "tamanho", "queda", "versão", "completude",
                      "recursos"):
            self.assertIn(check, text)


class StructureTest(WorldTest):
    def test_file_the_tool_refuses_is_a_problem(self):
        self.broken.add("carcara-GO.pmtiles")
        self.assertOneProblem(self.problems(), "estrutura", "carcara-GO.pmtiles")

    def test_light_packs_are_verified_too(self):
        self.broken.add("carcara-DF-leve.pmtiles")
        self.assertOneProblem(self.problems(), "estrutura", "carcara-DF-leve.pmtiles")


class HeaderTest(WorldTest):
    def test_raster_tiles_are_refused(self):
        self.headers["carcara-DF.pmtiles"] = {"tile_type": "png"}
        self.assertOneProblem(self.problems(), "cabeçalho", "carcara-DF.pmtiles", "png")

    def test_other_compression_is_refused(self):
        self.headers["carcara-DF.pmtiles"] = {"tile_compression": "brotli"}
        self.assertOneProblem(self.problems(), "cabeçalho", "brotli")

    def test_each_kind_of_pack_has_its_zooms(self):
        self.headers["carcara-DF-leve.pmtiles"] = {"maxzoom": 15}
        self.headers["carcara-base.pmtiles"] = {"maxzoom": 10}
        problems = self.problems()
        self.assertEqual(2, len(problems), problems)
        self.assertTrue(any("carcara-DF-leve.pmtiles" in p and "13" in p for p in problems))
        self.assertTrue(any("carcara-base.pmtiles" in p and "9" in p for p in problems))

    def test_pack_that_does_not_start_at_zoom_0_is_refused(self):
        self.headers["carcara-GO.pmtiles"] = {"minzoom": 8}
        self.assertOneProblem(self.problems(), "cabeçalho", "carcara-GO.pmtiles")

    def test_bounds_must_cover_the_state(self):
        # Um recorte feito com a malha errada: o retângulo do arquivo não cobre o estado.
        self.headers["carcara-GO.pmtiles"] = {"bounds": (-50.0, -17.0, -49.0, -16.0)}
        self.assertOneProblem(self.problems(), "cabeçalho", "carcara-GO.pmtiles", "não cobre")

    def test_base_must_cover_every_state(self):
        self.headers["carcara-base.pmtiles"] = {"bounds": (-48.5, -16.2, -47.0, -15.3)}
        self.assertOneProblem(self.problems(), "cabeçalho", "carcara-base.pmtiles", "não cobre")

    def test_unclustered_file_is_refused(self):
        self.headers["carcara-DF.pmtiles"] = {"clustered": False}
        self.assertOneProblem(self.problems(), "cabeçalho", "clustered")


class ContentTest(WorldTest):
    def test_missing_street_tile_over_the_capital(self):
        self.tiles[("carcara-GO.pmtiles", *self.capital_tile("GO", 15))] = None
        self.assertOneProblem(self.problems(), "conteúdo", "carcara-GO.pmtiles", "Goiânia")

    def test_street_tile_without_roads(self):
        self.tiles[("carcara-DF.pmtiles", *self.capital_tile("DF", 15))] = mvt_builder.tile({"earth": 1, "roads": 0})
        self.assertOneProblem(self.problems(), "conteúdo", "roads", "Brasília")

    def test_city_tile_without_places(self):
        self.tiles[("carcara-DF.pmtiles", *self.capital_tile("DF", 12))] = mvt_builder.tile({"roads": 4})
        self.assertOneProblem(self.problems(), "conteúdo", "places")

    def test_tile_that_does_not_decode(self):
        self.tiles[("carcara-DF.pmtiles", *self.capital_tile("DF", 15))] = b"\x1f\x8b\x08\x00lixo"
        self.assertOneProblem(self.problems(), "conteúdo", "carcara-DF.pmtiles")

    def test_light_pack_is_checked_at_its_own_deepest_zoom(self):
        self.tiles[("carcara-DF-leve.pmtiles", *self.capital_tile("DF", 13))] = None
        self.assertOneProblem(self.problems(), "conteúdo", "carcara-DF-leve.pmtiles")

    def test_base_is_checked_too(self):
        self.tiles[("carcara-base.pmtiles", *self.capital_tile("DF", 9))] = mvt_builder.tile({"earth": 1})
        self.assertOneProblem(self.problems(), "conteúdo", "carcara-base.pmtiles")


class BorderTest(WorldTest):
    def border_tiles(self):
        point = validation.border_point(DF, GO)
        return [(zoom, *mvt.tile_at(point.y, point.x, zoom)) for zoom in validation.BORDER_ZOOMS]

    def test_neighbours_are_found_from_the_polygons(self):
        self.assertEqual([("DF", "GO")], validation.neighbours(POLYGONS, ["DF", "GO", "SP"]))
        self.assertEqual([], validation.neighbours(POLYGONS, ["DF", "SP"]))

    def test_border_point_is_on_the_border(self):
        point = validation.border_point(DF, GO)
        self.assertLess(DF.distance(point), 1e-3)
        self.assertLess(GO.distance(point), 1e-3)

    def test_border_tile_that_differs_between_neighbours(self):
        self.tiles[("carcara-GO.pmtiles", *self.border_tiles()[0])] = mvt_builder.tile({"roads": 9, "places": 9})
        self.assertOneProblem(self.problems(), "divisa", "DF", "GO")

    def test_border_tile_missing_from_one_of_them(self):
        self.tiles[("carcara-DF.pmtiles", *self.border_tiles()[1])] = None
        self.assertOneProblem(self.problems(), "divisa", "carcara-DF.pmtiles")

    def test_states_that_do_not_touch_are_not_compared(self):
        self.states = ["DF", "GO", "SP"]
        self.generated["SP"] = self.pack("carcara-SP.pmtiles", "carcara-SP-leve.pmtiles")
        self.assertEqual([], self.problems(states=self.states))
        compared = {call.args[0].name for call in extraction.read_tile.call_args_list
                    if call.args[1:] in [tuple(t) for t in self.border_tiles()]}
        self.assertNotIn("carcara-SP.pmtiles", compared)


class SizeTest(WorldTest):
    def test_file_at_the_release_limit_is_refused(self):
        with mock.patch.object(config, "MAX_ASSET_BYTES", 400):
            problems = self.problems()
        self.assertTrue(all("tamanho" in p for p in problems), problems)
        # DF, GO e a base têm 500 bytes e os recursos passam disso; os leves têm 100.
        flagged = sorted(p.split(": ")[1].split(" tem ")[0] for p in problems)
        self.assertEqual(["carcara-DF.pmtiles", "carcara-GO.pmtiles", "carcara-base.pmtiles",
                          "carcara-recursos.tar.gz"], flagged)


class DropTest(WorldTest):
    def published(self, tiles=1000, size=500, light_tiles=300):
        state = {"file": "x", "bytes": size, "tiles": tiles, "light": {"file": "y", "bytes": 100, "tiles": light_tiles}}
        return {"build_id": "2026-09-02-aaaaaaaa", "states": {"DF": dict(state), "GO": dict(state)},
                "base": {"file": "b", "bytes": size, "tiles": tiles}}

    def test_same_numbers_as_published_pass(self):
        self.assertEqual([], self.problems(published=self.published()))

    def test_pack_that_lost_tiles_is_refused(self):
        self.assertTrue(all("queda" in p and "tiles" in p for p in self.problems(published=self.published(tiles=1100))))
        self.assertEqual(3, len(self.problems(published=self.published(tiles=1100))))

    def test_small_loss_is_tolerated(self):
        self.assertEqual([], self.problems(published=self.published(tiles=1040)))

    def test_pack_that_lost_bytes_is_refused(self):
        problems = self.problems(published=self.published(size=600))
        self.assertEqual(3, len(problems), problems)
        self.assertTrue(all("bytes" in p for p in problems))

    def test_light_pack_is_compared_too(self):
        problems = self.problems(published=self.published(light_tiles=400))
        self.assertEqual(2, len(problems), problems)
        self.assertTrue(all("-leve" in p for p in problems))

    def test_accept_drop_lets_it_pass_and_says_so(self):
        self.assertEqual([], self.problems(published=self.published(tiles=1100), accept_drop=True))
        self.assertTrue(any("--accept-drop" in line for line in self.log), self.log)

    def test_first_generation_has_nothing_to_compare_and_says_so(self):
        self.assertEqual([], self.problems(published=None))
        self.assertTrue(any("primeira geração" in line for line in self.log), self.log)

    def test_state_new_in_this_generation_is_not_a_drop(self):
        published = self.published()
        del published["states"]["GO"]
        self.assertEqual([], self.problems(published=published))


class VersionTest(WorldTest):
    def test_other_major_version_is_refused(self):
        self.versions["carcara-GO.pmtiles"] = "5.0.0"
        self.assertOneProblem(self.problems(), "versão", "carcara-GO.pmtiles", "5.0.0")

    def test_other_major_version_is_refused_even_when_the_build_says_the_same(self):
        # O índice de builds já recusa outra versão maior; se um build assim chegasse até aqui, os pacotes também
        # seriam barrados, um por um.
        for name in ("carcara-DF.pmtiles", "carcara-DF-leve.pmtiles", "carcara-GO.pmtiles", "carcara-GO-leve.pmtiles",
                     "carcara-base.pmtiles"):
            self.versions[name] = "5.0.0"
        problems = self.problems(build=dict(BUILD, version="5.0.0"))
        self.assertEqual(5, len(problems), problems)
        self.assertTrue(all("versão maior" in p for p in problems))

    def test_pack_of_another_build_version_is_refused(self):
        # Mesma versão maior, mas não é a do build desta geração: arquivo de outra geração no meio.
        self.versions["carcara-DF-leve.pmtiles"] = "4.14.0"
        self.assertOneProblem(self.problems(), "versão", "carcara-DF-leve.pmtiles", "4.14.0")


class CompletenessTest(WorldTest):
    def test_state_without_a_pack(self):
        del self.generated["GO"]
        self.assertTrue(any("completude" in p and "GO" in p for p in self.problems()))

    def test_base_without_a_pack(self):
        del self.generated["base"]
        self.assertTrue(any("completude" in p and "base" in p for p in self.problems()))

    def test_file_gone_from_the_disk(self):
        (self.dist / "carcara-DF.pmtiles").unlink()
        self.assertTrue(any("completude" in p and "carcara-DF.pmtiles" in p for p in self.problems()))

    def test_file_changed_since_it_was_recorded(self):
        (self.dist / "carcara-DF.pmtiles").write_bytes(b"menor")
        self.assertTrue(any("completude" in p and "carcara-DF.pmtiles" in p for p in self.problems()))

    def test_light_pack_missing_when_the_generation_has_them(self):
        self.generated["GO"]["light"] = None
        self.assertOneProblem(self.problems(), "completude", "GO", "leve")

    def test_no_light_packs_when_the_generation_has_none(self):
        for state in self.states:
            self.generated[state]["light"] = None
        self.assertEqual([], self.problems(light=False))

    def test_resources_missing(self):
        (self.dist / resources.FILE_NAME).unlink()
        self.assertTrue(any("carcara-recursos.tar.gz" in p for p in self.problems()))

    def test_missing_files_do_not_blow_up_the_other_checks(self):
        (self.dist / "carcara-GO.pmtiles").unlink()
        problems = self.problems()
        self.assertTrue(all(isinstance(p, str) for p in problems))
        self.assertTrue(any("completude" in p for p in problems))


class ResourcesTest(WorldTest):
    def rewrite(self, change):
        files = resource_files()
        change(files)
        archive = self.dist / resources.FILE_NAME
        resources.write_archive(files, archive)
        self.resources_pack["bytes"] = archive.stat().st_size

    def test_missing_glyph_range(self):
        self.rewrite(lambda files: files.pop("fonts/Noto Sans Medium/512-767.pbf"))
        self.assertOneProblem(self.problems(), "recursos", "fonts/Noto Sans Medium/512-767.pbf")

    def test_icon_the_reference_style_asks_for_is_missing(self):
        def change(files):
            names = [n for n in validation.required_icons("light") if n != "arrow"]
            files[f"{resources.SPRITES_FOLDER}light.json"] = sprite_index(names)
        self.rewrite(change)
        self.assertOneProblem(self.problems(), "recursos", "arrow", "light.json")

    def test_icon_outside_the_picture(self):
        self.rewrite(lambda files: files.update({f"{resources.SPRITES_FOLDER}dark@2x.png": png(5, 5)}))
        self.assertOneProblem(self.problems(), "recursos", "dark@2x")

    def test_sprite_index_that_is_not_json(self):
        self.rewrite(lambda files: files.update({f"{resources.SPRITES_FOLDER}white.json": b"<html>"}))
        self.assertOneProblem(self.problems(), "recursos", "white.json")

    def test_missing_licence(self):
        self.rewrite(lambda files: files.pop(resources.ICONS_LICENCE))
        self.assertOneProblem(self.problems(), "recursos", resources.ICONS_LICENCE)

    def test_archive_that_does_not_open(self):
        (self.dist / resources.FILE_NAME).write_bytes(b"isto nao e um tar")
        self.resources_pack["bytes"] = 17
        self.assertOneProblem(self.problems(), "recursos", "carcara-recursos.tar.gz")

    def test_plain_flavours_only_need_the_core_icons(self):
        # As folhas claras de uma cor só não têm os ícones dos pontos de interesse, e os estilos delas não os pedem.
        self.assertIn("restaurant", validation.required_icons("light"))
        self.assertNotIn("restaurant", validation.required_icons("white"))
        self.assertIn("arrow", validation.required_icons("white"))
        self.assertIn("generic_shield-3char", validation.required_icons("black"))


class CapitalsTest(unittest.TestCase):
    def test_every_state_has_a_capital(self):
        self.assertEqual(sorted(config.STATES), sorted(validation.CAPITALS))

    def test_each_capital_falls_inside_its_state(self):
        mesh = config.RAW / "ibge_malha_uf.json"
        if not mesh.exists():
            self.skipTest("sem a malha do IBGE em data/raw (rode o gerador ou a medição uma vez)")
        polygons = regions.state_polygons(mesh)
        for state, (name, lat, lon) in validation.CAPITALS.items():
            self.assertTrue(polygons[state].contains(Point(lon, lat)), f"{name} fora de {state}")


if __name__ == "__main__":
    unittest.main()

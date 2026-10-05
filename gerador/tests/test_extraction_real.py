"""O recorte e a leitura do cabeçalho com o binário `pmtiles` de verdade, sobre um arquivo pequeno do repositório.

Sem o binário na versão fixada (CARCARA_PMTILES ou PATH), estes testes são pulados, com o motivo.
"""
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, extraction, pmtiles_tool  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bairro.pmtiles"


def tool_problem():
    try:
        pmtiles_tool.require()
    except RuntimeError as e:
        return str(e).splitlines()[0]
    return None


@unittest.skipIf(tool_problem(), f"sem o pmtiles fixado: {tool_problem()}")
class RealToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_header_of_the_fixture(self):
        header = extraction.header(FIXTURE)
        self.assertEqual("mvt", header.tile_type)
        self.assertEqual("gzip", header.tile_compression)
        self.assertEqual((14, 15), (header.minzoom, header.maxzoom))
        self.assertEqual((-47.886, -15.797, -47.882, -15.793), header.bounds)
        self.assertEqual(2, header.addressed_tiles)
        self.assertEqual(2, header.tile_entries)
        self.assertTrue(header.clustered)

    def test_metadata_carries_the_tileset_version_and_the_data_date(self):
        metadata = extraction.metadata(FIXTURE)
        self.assertRegex(metadata["version"], r"^4\.\d+\.\d+$")
        self.assertRegex(metadata["planetiler:osm:osmosisreplicationtime"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertIn("roads", [layer["id"] for layer in metadata["vector_layers"]])

    def test_the_whole_credit_is_written_and_nothing_else_changes(self):
        # Decisão do dono em 2026-10-05: o crédito do ESA WorldCover (CC BY 4.0) também dentro de cada arquivo, no
        # campo que o MapLibre mostra sozinho; antes ia o da origem, só o OpenStreetMap.
        dest = self.folder / "recorte.pmtiles"
        shutil.copyfile(FIXTURE, dest)
        extraction.set_attribution(dest, config.EMBEDDED_ATTRIBUTION)
        original, cut = extraction.metadata(FIXTURE), extraction.metadata(dest)
        self.assertEqual(config.EMBEDDED_ATTRIBUTION, cut["attribution"])
        self.assertIn("OpenStreetMap", cut["attribution"])
        self.assertIn("ESA WorldCover", cut["attribution"])
        for key in ("version", "vector_layers", "planetiler:osm:osmosisreplicationtime", "name"):
            self.assertEqual(original[key], cut[key], key)
        extraction.verify(dest)
        for z in (14, 15):
            n = 2 ** z
            x = int((-47.884 + 180) / 360 * n)
            y = int((1 - math.asinh(math.tan(math.radians(-15.795))) / math.pi) / 2 * n)
            self.assertIsNotNone(extraction.read_tile(FIXTURE, z, x, y))
            self.assertEqual(extraction.read_tile(FIXTURE, z, x, y), extraction.read_tile(dest, z, x, y), f"tile {z}/{x}/{y}")

    def test_verify_accepts_the_fixture(self):
        extraction.verify(FIXTURE)

    def test_verify_refuses_a_truncated_file(self):
        truncated = self.folder / "truncado.pmtiles"
        truncated.write_bytes(FIXTURE.read_bytes()[:40_000])
        with self.assertRaises(RuntimeError):
            extraction.verify(truncated)

    def test_header_of_something_else_is_an_error(self):
        other = self.folder / "texto.pmtiles"
        other.write_text("isto não é um arquivo de tiles")
        with self.assertRaises(RuntimeError) as ctx:
            extraction.header(other)
        self.assertIn("magic number", str(ctx.exception))  # o erro leva o que a ferramenta disse

    def test_extract_from_a_local_file_up_to_a_lower_zoom(self):
        # É assim que o pacote leve nasce: do arquivo completo já no disco, só com menos zooms.
        dest = self.folder / "menor.pmtiles"
        summary = extraction.extract(str(FIXTURE), dest, maxzoom=14)
        header = extraction.header(dest)
        self.assertEqual((14, 14), (header.minzoom, header.maxzoom))
        self.assertEqual(1, header.addressed_tiles)
        self.assertEqual(1, summary.tile_entries)
        self.assertFalse(dest.with_name(dest.name + ".parcial").exists())
        extraction.verify(dest)

    def test_read_tile_returns_the_stored_bytes(self):
        tile = extraction.read_tile(FIXTURE, 15, 12025, 17840)
        self.assertEqual(31557, len(tile))
        self.assertEqual(b"\x1f\x8b", tile[:2])  # gzip, como está no arquivo
        self.assertIsNone(extraction.read_tile(FIXTURE, 15, 0, 0))

    def test_extract_of_a_missing_source_leaves_nothing_behind(self):
        dest = self.folder / "nada.pmtiles"
        with self.assertRaises(RuntimeError):
            extraction.extract(str(self.folder / "nao-existe.pmtiles"), dest, maxzoom=14)
        self.assertEqual([], [p.name for p in self.folder.iterdir()])

    def test_two_extracts_of_the_same_source_are_identical(self):
        first, second = self.folder / "a.pmtiles", self.folder / "b.pmtiles"
        extraction.extract(str(FIXTURE), first, maxzoom=15)
        extraction.extract(str(FIXTURE), second, maxzoom=15)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        shutil.copy(first, self.folder / "c.pmtiles")


if __name__ == "__main__":
    unittest.main()

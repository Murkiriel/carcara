import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import extraction, config  # noqa: E402

# Saída real do `pmtiles extract --dry-run` (versão 1.31.2), recortando uma área pequena de um arquivo remoto.
DRY_RUN_OUTPUT = """\
2026/10/01 12:57:45 extract.go:401: fetching 8 dirs, 8 chunks, 7 requests
2026/10/01 12:57:49 extract.go:441: Region tiles 7868, result tile entries 7859
2026/10/01 12:57:49 extract.go:450: fetching 7859 tiles, 183 chunks, 35 requests
2026/10/01 12:57:49 extract.go:606: Completed in 5.334224s with 4 download threads (1473.3164561518226 tiles/s).
2026/10/01 12:57:49 extract.go:611: Extract required 45 total requests.
2026/10/01 12:57:49 extract.go:612: Extract transferred 50 MB (overfetch 0.05) for an archive size of 48 MB
"""


class ParseDryRunTest(unittest.TestCase):
    def test_reads_tiles_and_sizes(self):
        estimate = extraction.parse_dry_run(DRY_RUN_OUTPUT)
        self.assertEqual(7868, estimate.region_tiles)
        self.assertEqual(7859, estimate.tile_entries)
        self.assertEqual(48_000_000, estimate.archive_bytes)
        self.assertEqual(50_000_000, estimate.transfer_bytes)
        self.assertEqual(45, estimate.requests)

    def test_reads_other_units(self):
        # A ferramenta escreve tamanhos arredondados, em unidades decimais: "1.2 GB", "950 kB", "48 MB".
        text = DRY_RUN_OUTPUT.replace("transferred 50 MB", "transferred 1.3 GB").replace("size of 48 MB",
                                                                                         "size of 1.2 GB")
        estimate = extraction.parse_dry_run(text)
        self.assertEqual(1_200_000_000, estimate.archive_bytes)
        self.assertEqual(1_300_000_000, estimate.transfer_bytes)
        small = extraction.parse_dry_run(DRY_RUN_OUTPUT.replace("size of 48 MB", "size of 950 kB"))
        self.assertEqual(950_000, small.archive_bytes)

    def test_resolution_is_the_last_printed_digit(self):
        # Quem compara com um limite precisa saber o quanto o número pode estar arredondado.
        self.assertEqual(1_000_000, extraction.parse_dry_run(DRY_RUN_OUTPUT).archive_resolution)
        big = extraction.parse_dry_run(DRY_RUN_OUTPUT.replace("size of 48 MB", "size of 1.9 GB"))
        self.assertEqual(100_000_000, big.archive_resolution)

    def test_output_without_the_summary_is_an_error(self):
        truncated = "\n".join(DRY_RUN_OUTPUT.splitlines()[:3])
        with self.assertRaises(ValueError):
            extraction.parse_dry_run(truncated)

    def test_unknown_unit_is_an_error(self):
        with self.assertRaises(ValueError):
            extraction.parse_dry_run(DRY_RUN_OUTPUT.replace("size of 48 MB", "size of 48 XB"))


class FormatSizeTest(unittest.TestCase):
    """O tamanho em MB com as casas que a ferramenta informou, nem mais nem menos."""

    def test_keeps_only_the_digits_the_tool_gave(self):
        self.assertEqual("48 MB", extraction.format_size(48_000_000, 1_000_000))
        self.assertEqual("6,1 MB", extraction.format_size(6_100_000, 100_000))
        self.assertEqual("0,334 MB", extraction.format_size(334_000, 1_000))

    def test_sizes_in_gb_stay_in_mb_without_invented_digits(self):
        self.assertEqual("1200 MB", extraction.format_size(1_200_000_000, 100_000_000))


class DryRunCommandTest(unittest.TestCase):
    def run_with(self, returncode=0, output=DRY_RUN_OUTPUT):
        completed = mock.Mock(returncode=returncode, stdout=output)
        with mock.patch.object(extraction.subprocess, "run", return_value=completed) as run:
            with mock.patch.object(config, "PMTILES", "pmtiles-de-teste"):
                result = extraction.dry_run("https://exemplo.invalid/build.pmtiles", Path("GO.geojson"), 13)
        return run, result

    def test_command_never_downloads_tiles_and_keeps_four_threads(self):
        run, result = self.run_with()
        command = run.call_args.args[0]
        self.assertEqual(["pmtiles-de-teste", "extract", "https://exemplo.invalid/build.pmtiles"], command[:3])
        self.assertIn("--dry-run", command)
        self.assertIn("--region=GO.geojson", command)
        self.assertIn("--maxzoom=13", command)
        self.assertIn("--download-threads=4", command)
        self.assertEqual(7859, result.tile_entries)

    def test_failure_of_the_tool_is_an_error_with_its_output(self):
        with self.assertRaises(RuntimeError) as ctx:
            self.run_with(returncode=1, output="Failed to open remote archive")
        self.assertIn("Failed to open remote archive", str(ctx.exception))


# Saída real de um recorte de verdade: as mesmas linhas de resumo, no meio das linhas de progresso, que a
# ferramenta reescreve no lugar (retorno de carro, sem quebra de linha).
CR = chr(13)
EXTRACT_OUTPUT = "\n".join([
    "2026/10/01 13:24:19 extract.go:401: fetching 8 dirs, 8 chunks, 7 requests",
    "2026/10/01 13:24:24 extract.go:441: Region tiles 7868, result tile entries 7859",
    "2026/10/01 13:24:24 extract.go:450: fetching 7859 tiles, 183 chunks, 35 requests",
    "fetching chunks   0% |                    | ( 0 B/48 MB) [0s:0s]" + CR
    + "fetching chunks  52% |##########          | (25/48 MB, 6.2 MB/s) [4s:3s]" + CR
    + "fetching chunks 100% |####################| (48/48 MB, 6.0 MB/s)",
    "2026/10/01 13:24:32 extract.go:606: Completed in 14.4522404s with 4 download threads (543.79 tiles/s).",
    "2026/10/01 13:24:32 extract.go:611: Extract required 45 total requests.",
    "2026/10/01 13:24:32 extract.go:612: Extract transferred 50 MB (overfetch 0.05) for an archive size of 48 MB",
    ""])

SHOW_OUTPUT = """\
pmtiles spec version: 3
tile type: mvt
bounds: (long: -48.335697, lat: -16.100000) (long: -47.258503, lat: -15.451800)
min zoom: 0
max zoom: 15
center: (long: -47.797100, lat: -15.775900)
center zoom: 0
addressed tiles count: 7868
tile entries count: 7859
tile contents count: 7818
clustered: true
internal compression: gzip
tile compression: gzip
version 4.15.2
"""

HEADER_JSON = """{
    "tile_compression": "gzip",
    "tile_type": "mvt",
    "minzoom": 0,
    "maxzoom": 15,
    "bounds": [-48.335697, -16.0999999, -47.2585026, -15.4518],
    "center": [-47.7970998, -15.7759, 0]
}"""


class ParseExtractTest(unittest.TestCase):
    def test_summary_is_read_through_the_progress_lines(self):
        summary = extraction.parse_dry_run(EXTRACT_OUTPUT)
        self.assertEqual(7859, summary.tile_entries)
        self.assertEqual(50_000_000, summary.transfer_bytes)
        self.assertEqual(45, summary.requests)


class ParseHeaderTest(unittest.TestCase):
    def test_header_joins_the_json_and_the_counts(self):
        header = extraction.parse_header(HEADER_JSON, SHOW_OUTPUT)
        self.assertEqual("mvt", header.tile_type)
        self.assertEqual("gzip", header.tile_compression)
        self.assertEqual((0, 15), (header.minzoom, header.maxzoom))
        self.assertEqual((-48.335697, -16.0999999, -47.2585026, -15.4518), header.bounds)  # oeste, sul, leste, norte
        self.assertEqual(7868, header.addressed_tiles)
        self.assertEqual(7859, header.tile_entries)
        self.assertEqual(7818, header.tile_contents)
        self.assertTrue(header.clustered)

    def test_not_clustered_is_read_as_such(self):
        header = extraction.parse_header(HEADER_JSON, SHOW_OUTPUT.replace("clustered: true", "clustered: false"))
        self.assertFalse(header.clustered)

    def test_missing_counts_are_an_error(self):
        with self.assertRaises(ValueError):
            extraction.parse_header(HEADER_JSON, "pmtiles spec version: 3")

    def test_header_that_is_not_json_is_an_error(self):
        with self.assertRaises(ValueError):
            extraction.parse_header("Failed to show archive", SHOW_OUTPUT)


class ExtractCommandTest(unittest.TestCase):
    """O comando do recorte de verdade, com o `pmtiles` no lugar de um dublê que grava (ou não) o arquivo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self._tmp.name) / "carcara-DF.pmtiles"
        self.commands = []

    def tearDown(self):
        self._tmp.cleanup()

    def fake_tool(self, returncode=0, output=EXTRACT_OUTPUT, writes=b"tiles"):
        def run(command, **kwargs):
            self.commands.append(command)
            if command[1] == "extract" and writes is not None:
                Path(command[3]).write_bytes(writes)
            return mock.Mock(returncode=returncode, stdout=output)
        return mock.patch.object(extraction.subprocess, "run", side_effect=run)

    def test_extract_by_region_from_a_remote_build(self):
        with self.fake_tool(), mock.patch.object(config, "PMTILES", "pmtiles-de-teste"):
            summary = extraction.extract("https://exemplo.invalid/build.pmtiles", self.dest, maxzoom=15,
                                         region=Path("DF.geojson"))
        command = self.commands[0]
        self.assertEqual(["pmtiles-de-teste", "extract", "https://exemplo.invalid/build.pmtiles"], command[:3])
        self.assertIn("--region=DF.geojson", command)
        self.assertIn("--maxzoom=15", command)
        self.assertIn("--download-threads=4", command)
        self.assertNotIn("--dry-run", command)
        self.assertEqual(7859, summary.tile_entries)
        self.assertEqual(b"tiles", self.dest.read_bytes())

    def test_the_file_only_gets_its_name_when_complete(self):
        # O recorte grava num nome provisório; o nome final só aparece com o arquivo inteiro.
        with self.fake_tool():
            extraction.extract("origem.pmtiles", self.dest, maxzoom=13)
        self.assertTrue(self.commands[0][3].endswith(".parcial"))
        self.assertEqual(["carcara-DF.pmtiles"], [p.name for p in self.dest.parent.iterdir()])

    def test_without_a_region_none_is_passed(self):
        with self.fake_tool():
            extraction.extract("origem.pmtiles", self.dest, maxzoom=13)
        self.assertFalse(any(arg.startswith("--region") for arg in self.commands[0]))

    def test_failure_leaves_neither_the_file_nor_the_partial(self):
        with self.fake_tool(returncode=1, output="Failed to extract"):
            with self.assertRaises(RuntimeError) as ctx:
                extraction.extract("origem.pmtiles", self.dest, maxzoom=13)
        self.assertIn("Failed to extract", str(ctx.exception))
        self.assertEqual([], list(self.dest.parent.iterdir()))

    def test_success_without_a_file_is_an_error(self):
        with self.fake_tool(writes=None):
            with self.assertRaises(RuntimeError):
                extraction.extract("origem.pmtiles", self.dest, maxzoom=13)

    def test_an_old_file_is_replaced_not_mixed(self):
        self.dest.write_bytes(b"geracao antiga")
        with self.fake_tool(writes=b"geracao nova"):
            extraction.extract("origem.pmtiles", self.dest, maxzoom=13)
        self.assertEqual(b"geracao nova", self.dest.read_bytes())

    def test_verify_failure_is_an_error_with_the_tool_output(self):
        with self.fake_tool(returncode=1, output="Failed to verify archive, out of bounds"):
            with self.assertRaises(RuntimeError) as ctx:
                extraction.verify(self.dest)
        self.assertIn("out of bounds", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

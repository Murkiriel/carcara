import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import sources, config  # noqa: E402
from tests.fake_server import FakeServer  # noqa: E402


def fake_mesh(exclude=()) -> bytes:
    """GeoJSON no formato da API de malhas do IBGE: uma feição por UF, código em `codarea`."""
    features = [{"type": "Feature", "properties": {"codarea": code},
                 "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
                for code in config.IBGE_STATE_CODES if code not in exclude]
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


class MeshTest(unittest.TestCase):
    """sources.ibge_mesh: só grava (e só aceita do cache) uma malha com as 27 UFs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raw = Path(self._tmp.name)
        self.dest = self.raw / "ibge_malha_uf.json"
        self.server = FakeServer().__enter__()
        self.server.files["/malha"] = fake_mesh()
        self._patches = [mock.patch.object(config, "RAW", self.raw),
                         mock.patch.object(config, "IBGE_MESH_URL", self.server.url("/malha")),
                         mock.patch.object(sources, "RETRY_DELAY", 0)]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.server.__exit__(None, None, None)
        self._tmp.cleanup()

    def downloads(self):
        return sum(1 for path, _ in self.server.requests if path == "/malha")

    def test_good_mesh_is_saved(self):
        self.assertEqual(self.dest, sources.ibge_mesh())
        self.assertEqual(27, len(json.loads(self.dest.read_text())["features"]))

    def test_gzip_mesh_is_saved_decompressed(self):
        # O IBGE manda a malha comprimida para os executores do GitHub Actions, mesmo sem o cliente pedir.
        self.server.gzip_always.add("/malha")
        sources.ibge_mesh()
        self.assertEqual(27, len(json.loads(self.dest.read_text())["features"]))

    def test_error_page_with_200_is_not_saved(self):
        self.server.files["/malha"] = b"<html><body>Servico indisponivel</body></html>"
        with self.assertRaises(RuntimeError):
            sources.ibge_mesh()
        self.assertFalse(self.dest.exists())

    def test_mesh_missing_a_state_is_rejected(self):
        self.server.files["/malha"] = fake_mesh(exclude=("53",))  # sem o DF
        with self.assertRaises(RuntimeError) as ctx:
            sources.ibge_mesh()
        self.assertIn("DF", str(ctx.exception))
        self.assertFalse(self.dest.exists())

    def test_invalid_cache_is_replaced(self):
        self.dest.write_text("<html>erro gravado por uma versão antiga</html>")
        sources.ibge_mesh()
        self.assertEqual(27, len(json.loads(self.dest.read_text())["features"]))
        self.assertEqual(1, self.downloads())

    def test_valid_cache_does_not_download(self):
        self.dest.write_bytes(fake_mesh())
        sources.ibge_mesh()
        self.assertEqual(0, self.downloads())


def build(key, uploaded, version="4.15.2", **extra):
    entry = {"key": key, "size": 138_000_000_000, "md5sum": "x", "b3sum": "ab" * 32, "uploaded": uploaded,
             "version": version}
    entry.update(extra)
    return entry


class LatestBuildTest(unittest.TestCase):
    """sources.latest_build: a entrada mais recente do índice de builds, só se for do esquema esperado."""

    def setUp(self):
        self.server = FakeServer().__enter__()
        self._patches = [mock.patch.object(config, "BUILDS_INDEX_URL", self.server.url("/builds.json")),
                         mock.patch.object(config, "BUILD_BASE_URL", "https://exemplo.invalid/"),
                         mock.patch.object(sources, "RETRY_DELAY", 0)]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.server.__exit__(None, None, None)

    def publish(self, entries):
        self.server.files["/builds.json"] = json.dumps(entries).encode()

    def test_picks_the_most_recent_upload(self):
        # O índice não vem em ordem: a escolha é pela data de envio, não pela posição.
        self.publish([build("20230918.pmtiles", "2023-09-18T10:00:00.000Z", version="3.0.0"),
                      build("20261001.pmtiles", "2026-10-01T08:53:09.033Z"),
                      build("20260930.pmtiles", "2026-09-30T08:58:27.530Z")])
        latest = sources.latest_build()
        self.assertEqual("20261001.pmtiles", latest["key"])
        self.assertEqual("https://exemplo.invalid/20261001.pmtiles", latest["url"])
        self.assertEqual("4.15.2", latest["version"])
        self.assertEqual("ab" * 32, latest["b3sum"])
        self.assertEqual("2026-10-01T08:53:09.033Z", latest["uploaded"])
        self.assertEqual(138_000_000_000, latest["size"])

    def test_other_major_version_is_refused(self):
        self.publish([build("20270101.pmtiles", "2027-01-01T09:00:00.000Z", version="5.0.0"),
                      build("20261001.pmtiles", "2026-10-01T08:53:09.033Z")])
        with self.assertRaises(RuntimeError) as ctx:
            sources.latest_build()
        self.assertIn("5.0.0", str(ctx.exception))

    def test_empty_index_is_refused(self):
        self.publish([])
        with self.assertRaises(RuntimeError):
            sources.latest_build()

    def test_index_that_is_not_a_list_is_refused(self):
        self.server.files["/builds.json"] = b"<html>manutencao</html>"
        with self.assertRaises(RuntimeError):
            sources.latest_build()

    def test_entry_without_b3sum_is_refused(self):
        entry = build("20261001.pmtiles", "2026-10-01T08:53:09.033Z")
        del entry["b3sum"]
        self.publish([entry])
        with self.assertRaises(RuntimeError) as ctx:
            sources.latest_build()
        self.assertIn("b3sum", str(ctx.exception))

    def test_key_with_path_is_refused(self):
        # O `key` vira parte de um endereço: só um nome de arquivo simples é aceito.
        self.publish([build("../outro/20261001.pmtiles", "2026-10-01T08:53:09.033Z")])
        with self.assertRaises(RuntimeError):
            sources.latest_build()


if __name__ == "__main__":
    unittest.main()

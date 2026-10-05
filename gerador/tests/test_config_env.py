"""O que o config fixa e o que ele lê do ambiente."""
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config  # noqa: E402

ENV_VARS = ("CARCARA_PMTILES", "CARCARA_KEEP_GENERATIONS", "CARCARA_DOWNLOAD_THREADS")


def reload_config(**env):
    clean = {k: v for k, v in os.environ.items() if k not in ENV_VARS}
    with mock.patch.dict(os.environ, {**clean, **env}, clear=True):
        return importlib.reload(config)


class EnvironmentTest(unittest.TestCase):
    def tearDown(self):
        importlib.reload(config)  # devolve o config ao que o ambiente de verdade manda, para os outros testes

    def test_tool_from_the_path_by_default(self):
        self.assertEqual("pmtiles", reload_config().PMTILES)

    def test_tool_from_the_environment(self):
        self.assertEqual("/opt/pmtiles/pmtiles", reload_config(CARCARA_PMTILES="/opt/pmtiles/pmtiles").PMTILES)

    def test_kept_generations(self):
        self.assertEqual(3, reload_config().KEEP_GENERATIONS)
        self.assertEqual(5, reload_config(CARCARA_KEEP_GENERATIONS="5").KEEP_GENERATIONS)
        self.assertEqual(0, reload_config(CARCARA_KEEP_GENERATIONS="0").KEEP_GENERATIONS)  # 0 = não apaga

    def test_download_threads_cannot_be_raised_from_outside(self):
        # O build da Protomaps é um serviço gratuito: nenhuma variável de ambiente acelera os pedidos.
        self.assertEqual(4, reload_config(CARCARA_DOWNLOAD_THREADS="32").DOWNLOAD_THREADS)


class FixedValuesTest(unittest.TestCase):
    def test_zooms(self):
        self.assertEqual(15, config.MAX_ZOOM)
        self.assertEqual(13, config.LIGHT_MAX_ZOOM)
        self.assertEqual(9, config.BASE_MAX_ZOOM)

    def test_generation_interval(self):
        self.assertEqual(29, config.GENERATION_INTERVAL_DAYS)

    def test_asset_limit_leaves_room_below_the_release_limit(self):
        # O GitHub recusa arquivo de release a partir de 2 GiB.
        self.assertLess(config.MAX_ASSET_BYTES, 2 * 1024 ** 3)
        self.assertGreater(config.MAX_ASSET_BYTES, 1_500_000_000)

    def test_every_state_has_a_name_and_an_ibge_code(self):
        self.assertEqual(27, len(config.STATES))
        self.assertEqual(sorted(config.STATES), sorted(config.IBGE_STATE_CODES.values()))

    def test_tool_version_is_pinned_with_a_checksum_per_platform(self):
        self.assertRegex(config.PMTILES_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertIn(("Linux", "x86_64"), config.PMTILES_ASSETS)
        self.assertIn(("Windows", "x86_64"), config.PMTILES_ASSETS)
        for name, sha256 in config.PMTILES_ASSETS.values():
            self.assertIn(config.PMTILES_VERSION, name)
            self.assertRegex(sha256, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()

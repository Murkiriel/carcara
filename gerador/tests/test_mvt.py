import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import mvt  # noqa: E402
from tests import mvt_builder  # noqa: E402


class LayerCountTest(unittest.TestCase):
    def test_counts_the_features_of_each_layer(self):
        data = mvt_builder.tile({"roads": 3, "places": 1, "water": 0}, compressed=False)
        self.assertEqual({"roads": 3, "places": 1, "water": 0}, mvt.layer_feature_counts(data))

    def test_stored_tile_is_decompressed_first(self):
        self.assertEqual({"roads": 2}, mvt.read(mvt_builder.tile({"roads": 2})))

    def test_stored_tile_without_compression_is_read_as_is(self):
        self.assertEqual({"roads": 2}, mvt.read(mvt_builder.tile({"roads": 2}, compressed=False)))

    def test_empty_tile_has_no_layers(self):
        self.assertEqual({}, mvt.layer_feature_counts(b""))

    def test_garbage_is_an_error_not_an_empty_tile(self):
        # Bytes ainda compactados, ou um arquivo qualquer, não podem passar por "tile sem camadas".
        with self.assertRaises(ValueError):
            mvt.layer_feature_counts(b"\x1f\x8b\x08\x00isto nao e um tile")
        with self.assertRaises(ValueError):
            mvt.layer_feature_counts(mvt_builder.tile({"roads": 2}, compressed=False)[:-3])

    def test_well_formed_message_that_is_not_a_tile_is_an_error(self):
        # Um protobuf válido de outra coisa (aqui, um campo 1 no nível de cima) não é um tile sem camadas.
        with self.assertRaises(ValueError):
            mvt.layer_feature_counts(mvt_builder.field(1, b"outra mensagem"))

    def test_truncated_gzip_is_an_error(self):
        with self.assertRaises(ValueError):
            mvt.read(mvt_builder.tile({"roads": 2})[:-5])


class TileAddressTest(unittest.TestCase):
    def test_tile_of_a_point(self):
        # O centro de Brasília, conferido com a ferramenta: 15/12025/17840 e 14/6012/8920.
        self.assertEqual((12025, 17840), mvt.tile_at(-15.7942, -47.8825, 15))
        self.assertEqual((6012, 8920), mvt.tile_at(-15.7942, -47.8825, 14))
        self.assertEqual((0, 0), mvt.tile_at(-15.7942, -47.8825, 0))


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import regions, config  # noqa: E402

from shapely.geometry import Point, Polygon, box, shape  # noqa: E402

MARGIN = 0.05


def mesh_with(geometries: dict) -> bytes:
    """Malha no formato do IBGE com as geometrias dadas por UF; as outras UFs ganham um quadrado longe."""
    codes = {state: code for code, state in config.IBGE_STATE_CODES.items()}
    features = []
    for i, state in enumerate(sorted(codes)):
        geometry = geometries.get(state) or box(100 + 2 * i, 0, 101 + 2 * i, 1)
        features.append({"type": "Feature", "properties": {"codarea": codes[state]},
                         "geometry": json.loads(json.dumps(geometry.__geo_interface__))})
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


class MarginTest(unittest.TestCase):
    def test_margin_contains_the_whole_state(self):
        state = box(-48, -16, -47, -15)
        self.assertTrue(regions.with_margin(state, MARGIN).contains(state))

    def test_margin_reaches_just_outside_and_not_further(self):
        area = regions.with_margin(box(-48, -16, -47, -15), MARGIN)
        self.assertTrue(area.contains(Point(-46.96, -15.5)))   # 0,04° além da divisa
        self.assertFalse(area.contains(Point(-46.94, -15.5)))  # 0,06° além da divisa

    def test_distant_island_stays_a_separate_part(self):
        state = box(0, 0, 1, 1).union(box(5, 0, 5.2, 0.2))  # continente e ilha a 4° dele
        area = regions.with_margin(state, MARGIN)
        self.assertEqual("MultiPolygon", area.geom_type)
        self.assertEqual(2, len(area.geoms))

    def test_enclave_of_another_state_stays_out(self):
        # Um estado com outro dentro (GO em volta do DF): o miolo do buraco não entra no recorte do de fora.
        outer = Polygon(box(0, 0, 3, 3).exterior.coords, [box(1, 1, 2, 2).exterior.coords])
        area = regions.with_margin(outer, MARGIN)
        self.assertFalse(area.contains(Point(1.5, 1.5)))
        self.assertTrue(area.contains(Point(1.02, 1.5)))  # dentro da margem, já no vizinho


class PolygonsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        self.mesh = self.folder / "malha.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_state_polygons_are_keyed_by_state(self):
        self.mesh.write_bytes(mesh_with({"DF": box(-48, -16, -47, -15)}))
        polygons = regions.state_polygons(self.mesh)
        self.assertEqual(sorted(config.STATES), sorted(polygons))
        self.assertEqual((-48.0, -16.0, -47.0, -15.0), polygons["DF"].bounds)

    def test_brazil_covers_every_state_with_margin(self):
        self.mesh.write_bytes(mesh_with({"DF": box(-48, -16, -47, -15), "GO": box(-50, -18, -48, -14)}))
        polygons = regions.state_polygons(self.mesh)
        country = regions.brazil(polygons, MARGIN)
        for state, geometry in polygons.items():
            self.assertTrue(country.contains(regions.with_margin(geometry, MARGIN * 0.99)), state)

    def test_write_regions_writes_one_file_per_state_and_the_country(self):
        self.mesh.write_bytes(mesh_with({"DF": box(-48, -16, -47, -15)}))
        out = self.folder / "regioes"
        paths = regions.write_regions(self.mesh, out, MARGIN)
        self.assertEqual(sorted(list(config.STATES) + ["brasil"]), sorted(paths))
        self.assertEqual(out / "DF.geojson", paths["DF"])
        self.assertEqual(out / "brasil.geojson", paths["brasil"])
        self.assertEqual(28, len(list(out.glob("*.geojson"))))

    def test_region_file_is_a_bare_geometry_with_the_margin(self):
        # O `pmtiles extract --region` aceita a geometria solta (Polygon ou MultiPolygon), em longitude, latitude.
        self.mesh.write_bytes(mesh_with({"DF": box(-48, -16, -47, -15)}))
        paths = regions.write_regions(self.mesh, self.folder / "regioes", MARGIN)
        written = json.loads(paths["DF"].read_text(encoding="utf-8"))
        self.assertIn(written["type"], ("Polygon", "MultiPolygon"))
        min_lon, min_lat, max_lon, max_lat = shape(written).bounds
        self.assertAlmostEqual(-48.05, min_lon, places=6)
        self.assertAlmostEqual(-16.05, min_lat, places=6)
        self.assertAlmostEqual(-46.95, max_lon, places=6)
        self.assertAlmostEqual(-14.95, max_lat, places=6)

    def test_write_regions_clears_files_of_a_previous_run(self):
        self.mesh.write_bytes(mesh_with({}))
        out = self.folder / "regioes"
        out.mkdir()
        (out / "XX.geojson").write_text("{}")
        regions.write_regions(self.mesh, out, MARGIN)
        self.assertFalse((out / "XX.geojson").exists())


if __name__ == "__main__":
    unittest.main()

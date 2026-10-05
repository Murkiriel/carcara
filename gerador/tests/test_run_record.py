import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import run_record  # noqa: E402


class RunRecorderTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stages_are_recorded_in_order_with_their_status(self):
        recorder = run_record.RunRecorder(self.folder, interval=3600)
        with recorder.stage("prepare"):
            pass
        with self.assertRaises(RuntimeError):
            with recorder.stage("packs"):
                raise RuntimeError("caiu")
        recorder.save(self.folder / "geracao.json", "failed: RuntimeError: caiu")
        record = json.loads((self.folder / "geracao.json").read_text(encoding="utf-8"))
        self.assertEqual([("prepare", "ok"), ("packs", "failed")], [(s["stage"], s["status"]) for s in record["stages"]])
        self.assertEqual("failed: RuntimeError: caiu", record["result"])
        self.assertRegex(record["started_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_peak_disk_sees_files_written_during_a_stage(self):
        recorder = run_record.RunRecorder(self.folder, interval=3600)
        with recorder.stage("packs"):
            (self.folder / "grande.bin").write_bytes(b"x" * 2_000_000)
        recorder.save(self.folder / "geracao.json", "ok")
        record = json.loads((self.folder / "geracao.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(record["peak_disk_gb"], 0.002)

    def test_extra_numbers_go_into_the_record(self):
        recorder = run_record.RunRecorder(self.folder, interval=3600)
        recorder.note("transfer_bytes", 123)
        recorder.save(self.folder / "geracao.json", "ok")
        record = json.loads((self.folder / "geracao.json").read_text(encoding="utf-8"))
        self.assertEqual(123, record["transfer_bytes"])

    def test_folder_size_adds_up_nested_files(self):
        (self.folder / "a").mkdir()
        (self.folder / "a" / "1.bin").write_bytes(b"x" * 10)
        (self.folder / "2.bin").write_bytes(b"x" * 5)
        self.assertEqual(15, run_record.folder_size(self.folder))


if __name__ == "__main__":
    unittest.main()

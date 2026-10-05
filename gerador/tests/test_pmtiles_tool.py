import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config, pmtiles_tool  # noqa: E402
from tests.fake_server import FakeServer  # noqa: E402

BINARY = b"\x7fELF binario de mentira " * 200


def zip_with(members: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buffer.getvalue()


def tar_gz_with(members: dict) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AssetTest(unittest.TestCase):
    def test_windows_and_linux_have_a_pinned_archive(self):
        name, checksum = pmtiles_tool.asset_for("Windows", "AMD64")
        self.assertEqual(f"go-pmtiles_{config.PMTILES_VERSION}_Windows_x86_64.zip", name)
        self.assertEqual(64, len(checksum))
        name, _ = pmtiles_tool.asset_for("Linux", "x86_64")
        self.assertEqual(f"go-pmtiles_{config.PMTILES_VERSION}_Linux_x86_64.tar.gz", name)

    def test_platform_without_a_pinned_archive_is_an_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            pmtiles_tool.asset_for("Plan9", "mips")
        self.assertIn("Plan9", str(ctx.exception))


class InstallTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name) / "ferramenta"
        self.server = FakeServer().__enter__()
        self._patches = [mock.patch.object(config, "PMTILES_RELEASE_URL", self.server.url("/")),
                         mock.patch.object(pmtiles_tool, "RETRY_DELAY", 0)]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.server.__exit__(None, None, None)
        self._tmp.cleanup()

    def publish(self, system: str, name: str, archive: bytes, checksum=None):
        self.server.files["/" + name] = archive
        assets = {(system, "x86_64"): (name, checksum or sha256(archive))}
        patch = mock.patch.object(config, "PMTILES_ASSETS", assets)
        patch.start()
        self.addCleanup(patch.stop)

    def test_zip_is_checked_and_only_the_binary_is_extracted(self):
        self.publish("Windows", "f.zip", zip_with({"LICENSE": b"x", "README.md": b"y", "pmtiles.exe": BINARY}))
        path = pmtiles_tool.install(self.folder, system="Windows", machine="AMD64")
        self.assertEqual(self.folder / "pmtiles.exe", path)
        self.assertEqual(BINARY, path.read_bytes())
        self.assertEqual(["pmtiles.exe"], sorted(p.name for p in self.folder.iterdir()))

    def test_tar_gz_is_extracted_and_made_executable(self):
        self.publish("Linux", "f.tar.gz", tar_gz_with({"LICENSE": b"x", "pmtiles": BINARY}))
        path = pmtiles_tool.install(self.folder, system="Linux", machine="x86_64")
        self.assertEqual(self.folder / "pmtiles", path)
        self.assertEqual(BINARY, path.read_bytes())
        if os.name == "posix":
            self.assertTrue(os.access(path, os.X_OK))

    def test_wrong_checksum_installs_nothing(self):
        self.publish("Linux", "f.tar.gz", tar_gz_with({"pmtiles": BINARY}), checksum="0" * 64)
        with self.assertRaises(RuntimeError) as ctx:
            pmtiles_tool.install(self.folder, system="Linux", machine="x86_64")
        self.assertIn("sha256", str(ctx.exception))
        self.assertEqual([], [p.name for p in self.folder.iterdir()] if self.folder.exists() else [])

    def test_archive_without_the_binary_is_an_error(self):
        self.publish("Linux", "f.tar.gz", tar_gz_with({"LICENSE": b"x"}))
        with self.assertRaises(RuntimeError):
            pmtiles_tool.install(self.folder, system="Linux", machine="x86_64")

    def test_member_with_a_path_is_never_written(self):
        # Só o membro chamado exatamente `pmtiles` sai do arquivo: nada de extrair tudo o que vier dentro.
        self.publish("Linux", "f.tar.gz", tar_gz_with({"../fora/pmtiles": b"malicioso", "pmtiles": BINARY}))
        pmtiles_tool.install(self.folder, system="Linux", machine="x86_64")
        self.assertFalse((self.folder.parent / "fora").exists())
        self.assertEqual(BINARY, (self.folder / "pmtiles").read_bytes())


class VersionTest(unittest.TestCase):
    def run_with(self, output="", returncode=0, error=None):
        completed = mock.Mock(returncode=returncode, stdout=output)
        return mock.patch.object(pmtiles_tool.subprocess, "run", return_value=completed, side_effect=error)

    def test_reads_the_version_the_tool_prints(self):
        with self.run_with("pmtiles 1.31.2, commit a3e4951ea6a0477b784c27c1dcbfd9c130878c5a, built at 2026-07-22\n"):
            self.assertEqual("1.31.2", pmtiles_tool.installed_version("pmtiles"))

    def test_require_accepts_the_pinned_version(self):
        with self.run_with(f"pmtiles {config.PMTILES_VERSION}, commit abc, built at 2026-07-22\n"):
            pmtiles_tool.require("pmtiles")

    def test_require_refuses_another_version(self):
        # A leitura do que a ferramenta escreve foi conferida numa versão; outra pode escrever diferente.
        with self.run_with("pmtiles 1.99.0, commit abc, built at 2027-01-01\n"):
            with self.assertRaises(RuntimeError) as ctx:
                pmtiles_tool.require("pmtiles")
        self.assertIn("1.99.0", str(ctx.exception))
        self.assertIn(config.PMTILES_VERSION, str(ctx.exception))

    def test_require_says_how_to_install_when_the_tool_is_missing(self):
        with self.run_with(error=FileNotFoundError("pmtiles")):
            with self.assertRaises(RuntimeError) as ctx:
                pmtiles_tool.require("pmtiles")
        self.assertIn("install_pmtiles.py", str(ctx.exception))

    def test_unreadable_output_is_an_error(self):
        with self.run_with("comando desconhecido"):
            with self.assertRaises(RuntimeError):
                pmtiles_tool.installed_version("pmtiles")


class ActionsExportTest(unittest.TestCase):
    def test_writes_the_variable_for_the_next_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "github_env"
            env_file.write_text("OUTRA=1\n", encoding="utf-8")
            pmtiles_tool.export_to_actions(Path("/tmp/x/pmtiles"), str(env_file))
            lines = env_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual("OUTRA=1", lines[0])
            self.assertEqual(f"CARCARA_PMTILES={Path('/tmp/x/pmtiles')}", lines[1])

    def test_without_actions_nothing_is_written(self):
        pmtiles_tool.export_to_actions(Path("/tmp/x/pmtiles"), None)  # não lança


if __name__ == "__main__":
    unittest.main()

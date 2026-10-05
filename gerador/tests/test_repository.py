"""O que o repositório promete sobre si mesmo: licenças no lugar, dados gerados fora do git, e nenhum arquivo
rastreado com caminho de máquina local, e-mail pessoal ou o nome de quem usa os pacotes."""
import hashlib
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# Caminhos de máquina e e-mails pessoais. Montados em pedaços para este arquivo não casar com as próprias regras.
LOCAL_PATTERNS = [
    re.compile(r"[A-Za-z]:" + r"\\" + r"(Users|RE)" + r"\\"),
    re.compile("/" + "Users" + "/"),
    re.compile("App" + "Data"),
    re.compile(r"@(g" + r"mail|hot" + r"mail|out" + r"look|ya" + r"hoo)\."),
]

# Nomes que não podem aparecer em arquivo nenhum, guardados só pelo sha256 da palavra em minúsculas e sem
# separadores: a lista não revela o que proíbe.
FORBIDDEN_WORD_HASHES = {
    "7d1f49f334d419f1ac95a46661c8b712c699b3486decc57377c4f89ec8f94c4b",
}


def tracked_files():
    done = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True)
    if done.returncode != 0:
        return None
    return [REPO / name for name in done.stdout.decode("utf-8").split("\0") if name]


def words_and_pairs(text: str):
    """Cada palavra e cada par de palavras vizinhas, em minúsculas e colados ('Nome Composto' -> 'nomecomposto')."""
    words = re.findall(r"[a-zà-ÿ0-9]+", text.lower())
    yield from words
    for first, second in zip(words, words[1:]):
        yield first + second


def digest(word: str) -> str:
    return hashlib.sha256(word.encode("utf-8")).hexdigest()


class LicencesTest(unittest.TestCase):
    def test_data_licence_at_the_root(self):
        text = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Open Database License", text)

    def test_code_licence_in_the_generator(self):
        text = (REPO / "gerador" / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("MIT License"))


class IgnoredDataTest(unittest.TestCase):
    def test_generated_data_stays_out_of_git(self):
        self.assertIn("gerador/data/", (REPO / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_nothing_under_data_is_tracked(self):
        files = tracked_files()
        if files is None:
            self.skipTest("sem git: não dá para listar os arquivos rastreados")
        self.assertEqual([], [str(f.relative_to(REPO)) for f in files if "gerador/data/" in f.as_posix()])


class AnonymityTest(unittest.TestCase):
    """O repositório é independente e anônimo: nenhum arquivo rastreado traz caminho local, e-mail pessoal nem o nome
    de um aplicativo que use os pacotes."""

    @classmethod
    def setUpClass(cls):
        cls.files = tracked_files()

    def texts(self):
        if self.files is None:
            self.skipTest("sem git: não dá para listar os arquivos rastreados")
        for path in self.files:
            try:
                yield path, path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binário (fixture de tiles) ou arquivo apagado e ainda no índice

    def test_no_local_paths_nor_personal_addresses(self):
        found = []
        for path, text in self.texts():
            for pattern in LOCAL_PATTERNS:
                match = pattern.search(text)
                if match:
                    found.append(f"{path.relative_to(REPO)}: {match.group(0)!r}")
        self.assertEqual([], found)

    def test_no_forbidden_names(self):
        found = []
        for path, text in self.texts():
            if any(digest(word) in FORBIDDEN_WORD_HASHES for word in words_and_pairs(text)):
                found.append(str(path.relative_to(REPO)))
        self.assertEqual([], found)

    def test_the_word_check_sees_a_name_written_in_two_words(self):
        # Prova de que a verificação pega o que promete, com uma palavra qualquer no lugar do nome proibido.
        self.assertIn("nomecomposto", list(words_and_pairs("um Nome Composto aqui")))
        self.assertIn("nomecomposto", list(words_and_pairs("o nome-composto")))


if __name__ == "__main__":
    unittest.main()

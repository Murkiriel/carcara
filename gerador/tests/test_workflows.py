"""Os workflows do GitHub Actions: o que precisa continuar valendo neles, lido do texto dos arquivos (sem YAML)."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from carcara import config  # noqa: E402

WORKFLOWS = Path(__file__).resolve().parent.parent.parent / ".github" / "workflows"


def workflows():
    return {f.name: f.read_text(encoding="utf-8").replace("\r\n", "\n") for f in sorted(WORKFLOWS.glob("*.yml"))}


def code_lines(text: str):
    """As linhas do workflow sem os comentários (um comentário pode citar justamente o que não se deve fazer)."""
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


class RunnerTest(unittest.TestCase):
    def test_there_are_workflows(self):
        self.assertEqual(["gerar.yml", "testes.yml"], list(workflows()))

    def test_runner_image_is_pinned(self):
        """Imagem com versão, nunca `-latest`: quando o GitHub troca a imagem por trás do `ubuntu-latest`, o que foi
        testado numa máquina passa a rodar em outra."""
        for name, text in workflows().items():
            images = re.findall(r"^\s*runs-on:\s*(\S+)\s*$", text, flags=re.MULTILINE)
            self.assertTrue(images, f"{name}: nenhum runs-on")
            for image in images:
                self.assertRegex(image, r"^ubuntu-\d+\.\d+$", f"{name}: runs-on {image}")

    def test_actions_are_pinned_to_a_major_version(self):
        for name, text in workflows().items():
            uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)\s*$", text, flags=re.MULTILINE)
            self.assertTrue(uses, f"{name}: nenhuma action")
            for action in uses:
                self.assertRegex(action, r"^actions/[\w-]+@v\d+$", f"{name}: {action}")


class TestsWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.text = workflows()["testes.yml"]
        self.code = "\n".join(code_lines(self.text))

    def test_runs_the_whole_suite(self):
        self.assertIn("python -m unittest discover -s tests -t .", self.code)

    def test_installs_the_pinned_tool_with_the_checked_script(self):
        # A ferramenta vem do script que confere o sha256, nunca de um download solto no YAML.
        self.assertIn("python scripts/install_pmtiles.py", self.code)
        self.assertNotIn("curl", self.code)
        self.assertNotIn("wget", self.code)

    def test_installs_the_pinned_requirements(self):
        self.assertIn("pip install -r requirements.txt", self.code)

    def test_can_only_read_the_repository(self):
        self.assertRegex(self.code, r"permissions:\n\s+contents: read")
        self.assertNotIn("contents: write", self.code)

    def test_never_publishes_nor_generates(self):
        for forbidden in ("gh release", "publish.py", "generate.py", "git push"):
            self.assertNotIn(forbidden, self.code, forbidden)


def job(text: str, name: str) -> str:
    """O trecho de um job: da linha `  nome:` até o próximo job (ou o fim do arquivo)."""
    match = re.search(rf"^  {name}:\n(.*?)(?=^  \w[\w-]*:\n|\Z)", text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def step(job_text: str, name: str) -> str:
    """O trecho de um passo: do `- name:` dele até o próximo passo."""
    start = job_text.index(f"- name: {name}")
    following = re.search(r"^      - ", job_text[start + 1:], flags=re.MULTILINE)
    return job_text[start:start + 1 + following.start()] if following else job_text[start:]


class GenerationWorkflowTest(unittest.TestCase):
    """O workflow gerar roda todo dia e só segue para a geração quando a publicada completa o intervalo."""

    def setUp(self):
        self.text = workflows()["gerar.yml"]
        self.code = "\n".join(code_lines(self.text))
        self.interval = job(self.code, "interval")
        self.generate = job(self.code, "generate")

    def test_runs_every_day_away_from_minute_zero(self):
        """O GitHub atrasa e descarta disparos no começo da hora, quando está sob carga."""
        match = re.search(r'(?m)^  schedule:\n\s+- cron: "(\d+) (\d+) \* \* \*"', self.code)
        self.assertIsNotNone(match, "falta o cron diário")
        self.assertNotEqual("0", match.group(1))

    def test_can_still_be_started_by_hand(self):
        self.assertIn("  workflow_dispatch:\n", self.code)

    def test_manual_run_does_not_publish_by_default(self):
        # A opção inteira, linha a linha: um `default: false` de outra opção mais abaixo não serve.
        self.assertRegex(self.code, r"\n      publish:\n        description: [^\n]+\n        type: boolean\n"
                                    r"        default: false\n")

    def test_shrink_guard_is_on_by_default(self):
        """A trava do pacote que encolheu só sai quando alguém marca a opção; no agendamento, nunca."""
        self.assertRegex(self.code, r"\n      accept_drop:\n        description: [^\n]+\n        type: boolean\n"
                                    r"        default: false\n")
        self.assertIn("ACCEPT_DROP: ${{ inputs.accept_drop == true && '--accept-drop' || '' }}", self.generate)

    def test_interval_job_asks_the_tested_rule(self):
        self.assertTrue(self.interval, "falta o job interval")
        self.assertIn("scripts/due.py", self.interval)
        self.assertIn("run: ${{ steps.age.outputs.run }}", self.interval)

    def test_published_date_comes_from_the_checkout(self):
        """Com o repositório privado, raw.githubusercontent.com responde 404: a data sumiria."""
        self.assertIn("actions/checkout@", self.interval)
        self.assertNotIn("raw.githubusercontent.com", self.code)

    def test_scheduled_run_reads_the_catalog_of_the_branch_tip(self):
        """Um disparo agendado que espera na fila atrás de uma publicação tem de ver o catálogo novo, não o do
        commit em que foi disparado."""
        for name in ("interval", "generate"):
            self.assertIn("ref: ${{ github.event_name == 'schedule' && 'main' || github.ref }}", job(self.code, name),
                          name)

    def test_manual_run_always_generates(self):
        self.assertIn("github.event_name != 'schedule' && '--manual' || ''", self.interval)

    def test_a_fork_does_not_generate_on_schedule(self):
        self.assertIn("if: github.event_name != 'schedule' || github.repository == 'Murkiriel/carcara'", self.interval)

    def test_the_official_repository_is_the_one_the_generator_publishes_to(self):
        self.assertIn(f"github.repository == '{config.GITHUB_REPO}'", self.interval)

    def test_generation_waits_for_the_interval_job(self):
        self.assertIn("needs: interval\n", self.generate)
        self.assertIn("if: needs.interval.outputs.run == 'true'\n", self.generate)

    def test_scheduled_run_publishes_and_manual_only_if_asked(self):
        self.assertIn("PUBLISH: ${{ github.event_name == 'schedule' || inputs.publish == true }}", self.generate)
        publish_step = step(self.generate, "Publicar")
        self.assertIn("if: env.PUBLISH == 'true'\n", publish_step)
        self.assertIn("python scripts/publish.py --release --commit --push", publish_step)

    def test_robot_commits_with_the_anonymous_address(self):
        publish_step = step(self.generate, "Publicar")
        self.assertRegex(publish_step, r'git config user\.email "[^"]+@users\.noreply\.github\.com"')

    def test_one_generation_at_a_time(self):
        self.assertRegex(self.code, r"(?m)^concurrency:\n  group: generate\n  cancel-in-progress: false")

    def test_generates_with_the_pinned_tool_and_requirements(self):
        self.assertIn("pip install -r requirements.txt", self.generate)
        self.assertIn("python scripts/install_pmtiles.py", self.generate)
        self.assertIn("python generate.py", self.generate)
        self.assertNotIn("curl", self.code)
        self.assertNotIn("wget", self.code)

    def test_nothing_speeds_up_the_requests_to_the_build(self):
        self.assertNotIn("download-threads", self.code)
        self.assertNotIn("DOWNLOAD_THREADS", self.code)

    def test_what_the_person_types_never_goes_straight_into_a_command(self):
        """As opções do disparo à mão chegam aos comandos por variável de ambiente, nunca coladas no texto do
        comando: o que alguém digita no formulário não pode virar parte do script."""
        in_run = False
        for line in self.text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("run: |", "run: >")):
                in_run, indent = True, len(line) - len(line.lstrip())
                continue
            if in_run and stripped and len(line) - len(line.lstrip()) <= indent:
                in_run = False
            if in_run or stripped.startswith("run: "):
                self.assertNotIn("${{ inputs.", line, line)
                self.assertNotIn("${{ github.event.inputs.", line, line)

    def test_report_is_kept_even_when_the_generation_fails(self):
        # Os dois passos: o que junta os arquivos e o que os envia. Com um só deles, uma geração que falha fica sem
        # relatório, que é justamente quando ele faz falta.
        collect = step(self.generate, "Guardar o relatório da geração")
        self.assertIn("if: always()\n", collect)
        self.assertIn("geracao.json", collect)
        upload = self.generate[self.generate.index("- uses: actions/upload-artifact@"):]
        upload = upload[:upload.index("      - name: ")]
        self.assertIn("if: always()\n", upload)
        self.assertIn("retention-days:", upload)

    def test_only_this_workflow_may_write_to_the_repository(self):
        self.assertRegex(self.code, r"(?m)^permissions:\n  contents: write\n")


if __name__ == "__main__":
    unittest.main()

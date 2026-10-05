"""A regra do agendamento: gera de novo quando a geração publicada completa o intervalo (29 dias), e nunca gera
sozinho a primeira geração."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

GENERATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GENERATOR))
from carcara import config, schedule  # noqa: E402

BUILT = "2026-10-01T18:21:32Z"


def utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def after(**delta) -> datetime:
    return utc(BUILT) + timedelta(**delta)


class GenerationDueTest(unittest.TestCase):
    def due(self, built_at, now, status=schedule.OK, **kwargs):
        return schedule.generation_due(status, built_at, now, 29, **kwargs)[0]

    def test_default_interval_is_29_days(self):
        self.assertEqual(29, config.GENERATION_INTERVAL_DAYS)

    def test_28_days_is_too_early(self):
        self.assertFalse(self.due(BUILT, after(days=28)))

    def test_29_days_generates(self):
        self.assertTrue(self.due(BUILT, after(days=29)))

    def test_days_are_rounded(self):
        """28 dias e 13 h já contam como 29: o horário da geração não empurra a seguinte para o dia depois."""
        self.assertTrue(self.due(BUILT, after(days=28, hours=13)))
        self.assertFalse(self.due(BUILT, after(days=28, hours=11)))

    def test_scheduled_run_after_a_scheduled_generation(self):
        """Geração agendada termina por volta das 08:00 UTC; 29 dias depois, o agendamento das 07:17 já gera."""
        self.assertTrue(self.due("2026-10-30T08:00:00Z", utc("2026-11-28T07:17:00Z")))
        self.assertFalse(self.due("2026-10-30T08:00:00Z", utc("2026-11-27T07:17:00Z")))

    def test_no_published_generation_does_not_generate_on_schedule(self):
        # A primeira geração é sempre disparada à mão: o agendamento nunca publica uma primeira release sozinho.
        due, reason = schedule.generation_due(schedule.MISSING, None, after(days=100), 29)
        self.assertFalse(due)
        self.assertIn("à mão", reason)

    def test_unreadable_catalog_does_not_generate_on_schedule(self):
        due, reason = schedule.generation_due(schedule.UNREADABLE, None, after(days=100), 29)
        self.assertFalse(due)
        self.assertIn("catálogo", reason)

    def test_date_in_another_format_counts_as_unreadable(self):
        self.assertFalse(self.due("ontem", after(days=100)))

    def test_manual_always_generates(self):
        self.assertTrue(self.due(BUILT, after(hours=1), manual=True))
        self.assertTrue(self.due(None, after(hours=1), status=schedule.MISSING, manual=True))
        self.assertTrue(self.due(None, after(hours=1), status=schedule.UNREADABLE, manual=True))

    def test_reason_says_the_age(self):
        due, reason = schedule.generation_due(schedule.OK, BUILT, after(days=10), 29)
        self.assertFalse(due)
        self.assertIn("10 dias", reason)
        self.assertIn("29", reason)


class ExtraGenerationTest(unittest.TestCase):
    """Uma geração extra, fora do intervalo, como nos projetos irmãos: a partir do dia marcado, gera se a publicada
    for de antes dele, e tenta de novo nos dias seguintes se falhar; depois de publicar, não tem mais efeito."""

    PUBLISHED = "2026-10-05T14:19:28Z"
    MARKED = date(2026, 10, 6)

    def due(self, built_at, now, generate_from=MARKED, status=schedule.OK):
        return schedule.generation_due(status, built_at, utc(now), 29, generate_from=generate_from)

    def test_before_the_marked_day_it_waits(self):
        self.assertFalse(self.due(self.PUBLISHED, "2026-10-05T23:59:00Z")[0])

    def test_on_the_marked_day_it_generates(self):
        due, reason = self.due(self.PUBLISHED, "2026-10-06T06:17:00Z")
        self.assertTrue(due)
        self.assertIn("2026-10-06", reason)

    def test_keeps_trying_on_the_following_days_until_it_publishes(self):
        self.assertTrue(self.due(self.PUBLISHED, "2026-10-06T12:17:00Z")[0])
        self.assertTrue(self.due(self.PUBLISHED, "2026-10-08T06:17:00Z")[0])

    def test_once_published_it_has_no_effect(self):
        self.assertFalse(self.due("2026-10-06T06:40:00Z", "2026-10-06T12:17:00Z")[0])
        self.assertFalse(self.due("2026-10-06T06:40:00Z", "2026-10-07T06:17:00Z")[0])

    def test_the_interval_goes_on_counting_from_the_extra_generation(self):
        self.assertFalse(self.due("2026-10-06T06:40:00Z", "2026-11-03T06:17:00Z")[0])
        self.assertTrue(self.due("2026-10-06T06:40:00Z", "2026-11-04T06:17:00Z")[0])

    def test_without_a_marked_day_only_the_interval_counts(self):
        self.assertFalse(self.due(self.PUBLISHED, "2026-10-06T06:17:00Z", generate_from=None)[0])

    def test_a_marked_day_does_not_hold_back_the_interval(self):
        self.assertTrue(self.due("2026-09-01T07:10:00Z", "2026-10-01T06:17:00Z")[0])

    def test_a_marked_day_never_makes_the_first_generation(self):
        """A regra própria do Carcará vale também aqui: sem geração publicada, o agendamento não gera."""
        self.assertFalse(self.due(None, "2026-10-06T06:17:00Z", status=schedule.MISSING)[0])


class PublishedCatalogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.catalog = Path(self._tmp.name) / "catalogo.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_reads_built_at(self):
        self.catalog.write_text(json.dumps({"built_at": BUILT}), encoding="utf-8")
        self.assertEqual((schedule.OK, BUILT), schedule.read_published(self.catalog))

    def test_missing_catalog(self):
        self.assertEqual((schedule.MISSING, None), schedule.read_published(self.catalog))

    def test_broken_catalog(self):
        self.catalog.write_text("<html>", encoding="utf-8")
        self.assertEqual((schedule.UNREADABLE, None), schedule.read_published(self.catalog))

    def test_catalog_without_the_date(self):
        self.catalog.write_text(json.dumps({"schema": 1}), encoding="utf-8")
        self.assertEqual((schedule.UNREADABLE, None), schedule.read_published(self.catalog))

    def test_catalog_that_is_not_an_object(self):
        self.catalog.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual((schedule.UNREADABLE, None), schedule.read_published(self.catalog))


class DueScriptTest(unittest.TestCase):
    """A linha de comando que o workflow chama: imprime o motivo e grava run=true|false em $GITHUB_OUTPUT."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.output = self.tmp / "github_output"

    def tearDown(self):
        self._tmp.cleanup()

    def run_script(self, content, *args):
        catalog = self.tmp / "catalogo.json"
        catalog.unlink(missing_ok=True)
        self.output.unlink(missing_ok=True)  # o script acrescenta ao arquivo, como o Actions espera
        if content is not None:
            catalog.write_text(content, encoding="utf-8")
        env = {**os.environ, "GITHUB_OUTPUT": str(self.output)}
        done = subprocess.run([sys.executable, str(GENERATOR / "scripts" / "due.py"), "--catalog", str(catalog), *args],
                              capture_output=True, text=True, encoding="utf-8", env=env)
        # A data recusada pelo argparse sai antes de gravar a saída: nada gravado é "".
        written = self.output.read_text(encoding="utf-8") if self.output.exists() else ""
        return done.returncode, written, done.stdout

    def stamp(self, days_ago: int) -> str:
        built_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return json.dumps({"built_at": built_at})

    def test_recent_generation(self):
        code, output, log = self.run_script(self.stamp(3))
        self.assertEqual((0, "run=false\n"), (code, output))
        self.assertIn("3 dias", log)

    def test_old_generation(self):
        self.assertEqual((0, "run=true\n"), self.run_script(self.stamp(40))[:2])

    def test_no_catalog_does_not_run_and_is_not_an_error(self):
        code, output, log = self.run_script(None)
        self.assertEqual((0, "run=false\n"), (code, output))
        self.assertIn("à mão", log)

    def test_broken_catalog_does_not_run_and_fails_the_job(self):
        # Um catálogo estragado na raiz não pode passar em silêncio: o job fica vermelho, e ninguém gera por engano.
        code, output, _ = self.run_script("<html>")
        self.assertEqual("run=false\n", output)
        self.assertEqual(1, code)

    def test_manual(self):
        self.assertEqual((0, "run=true\n"), self.run_script(self.stamp(3), "--manual")[:2])
        self.assertEqual((0, "run=true\n"), self.run_script(None, "--manual")[:2])

    def test_extra_generation_from_the_command_line(self):
        self.assertEqual((0, "run=true\n"), self.run_script(self.stamp(3), "--generate-from", date.today().isoformat())[:2])
        self.assertEqual((0, "run=false\n"), self.run_script(self.stamp(3), "--generate-from", "")[:2])

    def test_a_bad_extra_date_is_an_error(self):
        self.assertEqual(2, self.run_script(self.stamp(3), "--generate-from", "amanha")[0])

    def test_interval_from_the_command_line(self):
        self.assertEqual((0, "run=true\n"), self.run_script(self.stamp(3), "--interval-days", "2")[:2])


if __name__ == "__main__":
    unittest.main()

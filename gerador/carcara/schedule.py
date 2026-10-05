"""Quando gerar de novo: a geração publicada tem uma data (`built_at` do catalogo.json da raiz), e o agendamento só
segue para a geração quando ela completa o intervalo. A linha de comando fica em scripts/due.py.

Diferente dos projetos irmãos, de propósito: **sem geração publicada, o agendamento não gera.** A primeira geração é
sempre disparada à mão, para a primeira release nunca sair sozinha. E um catálogo que não dá para ler também não
gera: quem decide é uma pessoa, e o job fica vermelho para ela ver.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

OK, MISSING, UNREADABLE = "ok", "missing", "unreadable"


def read_published(catalog: Path) -> Tuple[str, Optional[str]]:
    """(situação, built_at) do catálogo publicado: OK com a data; MISSING se o arquivo não existe; UNREADABLE se
    existe mas não é um catálogo com a data."""
    if not catalog.exists():
        return MISSING, None
    try:
        built_at = json.loads(catalog.read_text(encoding="utf-8")).get("built_at")
    except (OSError, ValueError, AttributeError):
        return UNREADABLE, None
    return (OK, built_at) if isinstance(built_at, str) else (UNREADABLE, None)


def generation_due(status: str, built_at: Optional[str], now: datetime, interval_days: int,
                   manual: bool = False) -> Tuple[bool, str]:
    """(gera?, motivo). Os dias são arredondados, para o horário da geração não empurrar a seguinte para o dia
    depois: uma geração que terminou às 08:00 conta 29 dias no agendamento das 07:17 do 29º dia."""
    if manual:
        return True, "disparado à mão: gera"
    if status == MISSING:
        return False, "nenhuma geração publicada: a primeira geração é disparada à mão, o agendamento não gera"
    try:
        if status != OK:
            raise ValueError(status)
        built = datetime.strptime(built_at or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False, ("o catálogo publicado não tem uma data legível: o agendamento não gera; conserte o catálogo "
                       "ou dispare à mão")
    days = (now - built + timedelta(hours=12)) // timedelta(days=1)
    if days >= interval_days:
        return True, f"geração publicada em {built_at} ({days} dias): gera"
    return False, f"geração publicada em {built_at} ({days} dias): ainda não, gera ao completar {interval_days} dias"


def is_readable(status: str, built_at: Optional[str]) -> bool:
    """A data do catálogo publicado pôde ser lida? (MISSING conta como lido: não há o que ler.)"""
    if status == MISSING:
        return True
    try:
        datetime.strptime(built_at or "", "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return status == OK

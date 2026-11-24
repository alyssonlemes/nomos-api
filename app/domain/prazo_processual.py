"""Cálculo de prazo a partir do texto de movimentação ou publicação.

A data recebida é a data do ato. Para publicação, o art. 224 do CPC trata o
primeiro dia útil seguinte como data da publicação e o dia útil seguinte a
esse como início da contagem. Feriados nacionais e fim de semana não contam.
Recesso forense e feriado local não entram nesta conta: o vencimento com
quantidade de dias é estimado e o advogado confirma no texto.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

_PRAZO_DIAS = re.compile(r"prazo\s+de\s+(\d{1,3})\s+dias?", re.IGNORECASE)
_RELEVANTE = re.compile(
    r"intima|cita[cç][aã]o|publica|despacho|decis[aã]o|senten[cç]a|"
    r"contestar|impugn|manifest|embargo|recurso|audi[eê]ncia|prazo",
    re.IGNORECASE,
)

STATUS_ABERTO = "aberto"
STATUS_CONFERIR = "conferir"
STATUS_NENHUM = "nenhum"
STATUS_CUMPRIDO = "cumprido"

@dataclass(frozen=True)
class PrazoCalculado:
    status: str
    dias: Optional[int]
    data_vencimento: Optional[date]

def apenas_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")

def normalizar_tipo(tipo: Optional[str]) -> str:
    if not tipo:
        return ""
    texto = unicodedata.normalize("NFD", tipo)
    sem_acento = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return sem_acento.strip().upper()

def extrair_dias_prazo(texto: str) -> Optional[int]:
    encontrado = _PRAZO_DIAS.search(texto or "")
    if not encontrado:
        return None
    dias = int(encontrado.group(1))
    if dias < 1 or dias > 365:
        return None
    return dias

def _pascoa(ano: int) -> date:
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)

def feriados_nacionais(ano: int) -> set[date]:
    pascoa = _pascoa(ano)
    return {
        date(ano, 1, 1),
        date(ano, 4, 21),
        date(ano, 5, 1),
        date(ano, 9, 7),
        date(ano, 10, 12),
        date(ano, 11, 2),
        date(ano, 11, 15),
        date(ano, 12, 25),
        pascoa - timedelta(days=2),
        pascoa + timedelta(days=60),
    }

def eh_dia_util(dia: date) -> bool:
    if dia.weekday() >= 5:
        return False
    return dia not in feriados_nacionais(dia.year)

def proximo_dia_util(dia: date) -> date:
    cursor = dia + timedelta(days=1)
    while not eh_dia_util(cursor):
        cursor += timedelta(days=1)
    return cursor

def somar_dias_uteis(inicio: date, dias: int) -> date:
    if dias < 1:
        raise ValueError("A quantidade de dias do prazo precisa ser positiva.")
    cursor = inicio
    restantes = dias
    while True:
        if eh_dia_util(cursor):
            restantes -= 1
            if restantes == 0:
                return cursor
        cursor += timedelta(days=1)

def calcular_vencimento(data_disponibilizacao: date, dias: int) -> date:
    publicacao = proximo_dia_util(data_disponibilizacao)
    inicio = proximo_dia_util(publicacao)
    return somar_dias_uteis(inicio, dias)

def decidir_prazo(
    *,
    tipo: Optional[str],
    conteudo: str,
    texto_extra: str = "",
    data_movimentacao: Optional[date] = None,
) -> PrazoCalculado:
    texto = " ".join(parte for parte in (conteudo, texto_extra) if parte)
    dias = extrair_dias_prazo(texto)
    tipo_norm = normalizar_tipo(tipo)
    relevante = tipo_norm == "PUBLICACAO" or _RELEVANTE.search(texto) is not None

    if dias and data_movimentacao:
        return PrazoCalculado(
            status=STATUS_ABERTO,
            dias=dias,
            data_vencimento=calcular_vencimento(data_movimentacao, dias),
        )
    if relevante:
        return PrazoCalculado(status=STATUS_CONFERIR, dias=dias, data_vencimento=None)
    return PrazoCalculado(status=STATUS_NENHUM, dias=None, data_vencimento=None)

"""Três planos por escritório. A landing não exibe estas opções.

O código fica na organização. Os limites são aplicados na API.
A troca de plano é feita no painel interno.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Plano:
    codigo: str
    nome: str
    usuarios: int
    processos: int

PLANO_PADRAO = "essencial"

PLANOS: dict[str, Plano] = {
    "essencial": Plano("essencial", "Essencial", usuarios=3, processos=50),
    "profissional": Plano("profissional", "Profissional", usuarios=10, processos=200),
    "escritorio": Plano("escritorio", "Escritório", usuarios=30, processos=800),
}

def obter_plano(codigo: str | None) -> Plano:
    if codigo and codigo in PLANOS:
        return PLANOS[codigo]
    return PLANOS[PLANO_PADRAO]

def cabe(em_uso: int, limite: int) -> bool:
    return em_uso < limite

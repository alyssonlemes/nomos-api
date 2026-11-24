"""Perfis de acesso com CRUD por módulo.

O comportamento segue o projeto Clinic: cada organização tem perfis de sistema
e uma matriz de visualizar/criar/editar/excluir por módulo. O perfil
Administrador permanece com acesso total.
"""

from typing import Any

MODULOS = (
    "dashboard",
    "clientes",
    "processos",
    "atividades",
    "jurimetria",
    "usuarios",
    "configuracoes",
)

ACOES = ("visualizar", "criar", "editar", "excluir")

# Módulos de consulta: a matriz só libera visualização.
SOMENTE_VISUALIZAR = frozenset({"dashboard", "jurimetria"})

NOME_ADMINISTRADOR = "Administrador"
NOME_GESTOR = "Gestor"
NOME_MEMBRO = "Membro"
NOME_VISUALIZADOR = "Visualizador"
NOME_ASSISTENTE = "Assistente"

# Papéis legados (coluna users.role / convites antigos) -> perfil.
NOME_POR_PAPEL = {
    "admin": NOME_ADMINISTRADOR,
    "owner": NOME_ADMINISTRADOR,
    "gestor": NOME_GESTOR,
    "member": NOME_MEMBRO,
    "membro": NOME_MEMBRO,
    "viewer": NOME_VISUALIZADOR,
    "visualizador": NOME_VISUALIZADOR,
    "assistant": NOME_ASSISTENTE,
    "assistente": NOME_ASSISTENTE,
    "administrador": NOME_ADMINISTRADOR,
}

def acoes(visualizar=False, criar=False, editar=False, excluir=False) -> dict:
    return {
        "visualizar": bool(visualizar),
        "criar": bool(criar),
        "editar": bool(editar),
        "excluir": bool(excluir),
    }

def acoes_vazias() -> dict:
    return acoes()

def todas_true() -> dict:
    return {modulo: acoes(True, True, True, True) for modulo in MODULOS}

def _limitar(modulo: str, valor: dict) -> dict:
    if modulo in SOMENTE_VISUALIZAR:
        return acoes(valor.get("visualizar", False))
    if modulo == "configuracoes":
        return acoes(valor.get("visualizar", False), False, valor.get("editar", False), False)
    return acoes(
        valor.get("visualizar", False),
        valor.get("criar", False),
        valor.get("editar", False),
        valor.get("excluir", False),
    )

def ler_acoes(valor: Any) -> dict:
    if not isinstance(valor, dict):
        return acoes_vazias()
    return acoes(
        valor.get("visualizar"),
        valor.get("criar"),
        valor.get("editar"),
        valor.get("excluir"),
    )

def permissoes_como_mapa(raw: Any, aplicar_limites: bool = True) -> dict:
    mapa = {modulo: acoes_vazias() for modulo in MODULOS}

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            modulo = item.get("modulo")
            if modulo in mapa:
                mapa[modulo] = ler_acoes(item)
    elif isinstance(raw, dict):
        for modulo, valor in raw.items():
            if modulo in mapa:
                mapa[modulo] = ler_acoes(valor)

    if aplicar_limites:
        for modulo in MODULOS:
            mapa[modulo] = _limitar(modulo, mapa[modulo])
    return mapa

def montar_permissoes(raw: Any, aplicar_limites: bool = True) -> list[dict]:
    mapa = permissoes_como_mapa(raw, aplicar_limites=aplicar_limites)
    return [{"modulo": modulo, **mapa[modulo]} for modulo in MODULOS]

def montar_permissoes_do_perfil(nome: str | None, raw: Any) -> list[dict]:
    if nome == NOME_ADMINISTRADOR:
        return montar_permissoes(todas_true(), aplicar_limites=False)
    return montar_permissoes(raw, aplicar_limites=True)

def tem_permissao(raw: Any, modulo: str, acao: str, nome_perfil: str | None = None) -> bool:
    if acao not in ACOES or modulo not in MODULOS:
        return False
    itens = montar_permissoes_do_perfil(nome_perfil, raw)
    item = next((entrada for entrada in itens if entrada["modulo"] == modulo), None)
    return bool(item and item.get(acao))

def _base() -> dict:
    return {modulo: acoes_vazias() for modulo in MODULOS}

def _com_modulos(overrides: dict) -> dict:
    mapa = _base()
    mapa.update(overrides)
    return mapa

PERFIS_PADRAO = [
    {
        "nome": NOME_ADMINISTRADOR,
        "descricao": "Acesso total à organização. A matriz deste perfil permanece liberada.",
        "isolate_data": False,
        "permissoes": todas_true(),
    },
    {
        "nome": NOME_GESTOR,
        "descricao": "Gerencia a operação do escritório e o perfil dos demais usuários.",
        "isolate_data": False,
        "permissoes": _com_modulos({
            "dashboard": acoes(True),
            "clientes": acoes(True, True, True, True),
            "processos": acoes(True, True, True, True),
            "atividades": acoes(True, True, True, True),
            "jurimetria": acoes(True),
            "usuarios": acoes(True, True, True, False),
            "configuracoes": acoes(True),
        }),
    },
    {
        "nome": NOME_MEMBRO,
        "descricao": "Atuação operacional. Vê apenas os próprios clientes e processos.",
        "isolate_data": True,
        "permissoes": _com_modulos({
            "dashboard": acoes(True),
            "clientes": acoes(True, True, True, True),
            "processos": acoes(True, True, True, True),
            "atividades": acoes(True, True, True, True),
            "jurimetria": acoes(True),
            "configuracoes": acoes(True),
        }),
    },
    {
        "nome": NOME_VISUALIZADOR,
        "descricao": "Somente leitura dos próprios clientes e processos.",
        "isolate_data": True,
        "permissoes": _com_modulos({
            "dashboard": acoes(True),
            "clientes": acoes(True),
            "processos": acoes(True),
            "atividades": acoes(True),
            "jurimetria": acoes(True),
            "configuracoes": acoes(True),
        }),
    },
    {
        "nome": NOME_ASSISTENTE,
        "descricao": "Apoio operacional, sem processos nem jurimetria. Vê apenas os próprios clientes.",
        "isolate_data": True,
        "permissoes": _com_modulos({
            "dashboard": acoes(True),
            "clientes": acoes(True, True, True, False),
            "atividades": acoes(True, True, True, False),
            "configuracoes": acoes(True),
        }),
    },
]

def nome_do_papel(role: str | None, eh_dono: bool = False) -> str:
    if eh_dono:
        return NOME_ADMINISTRADOR
    chave = (role or "").strip().lower()
    return NOME_POR_PAPEL.get(chave, NOME_MEMBRO)

def papel_legado(nome_perfil: str | None, eh_dono: bool = False) -> str:
    """Valor compatível com a coluna legada users.role e com o enum antigo."""
    if nome_perfil == NOME_ADMINISTRADOR and eh_dono:
        return "OWNER"
    if nome_perfil == NOME_ADMINISTRADOR:
        return "ADMIN"
    if nome_perfil == NOME_VISUALIZADOR:
        return "VIEWER"
    if nome_perfil == NOME_ASSISTENTE:
        return "ASSISTANT"
    return "MEMBER"

def papel_convite(nome_perfil: str | None) -> str:
    if nome_perfil == NOME_ADMINISTRADOR:
        return "admin"
    if nome_perfil == NOME_GESTOR:
        return "gestor"
    if nome_perfil == NOME_VISUALIZADOR:
        return "viewer"
    if nome_perfil == NOME_ASSISTENTE:
        return "assistant"
    return "member"

def _perfil(usuario: Any):
    return getattr(usuario, "profile", None)

def nome_perfil(usuario: Any) -> str | None:
    perfil = _perfil(usuario)
    if perfil is not None and getattr(perfil, "name", None):
        return perfil.name
    return None

def eh_administrador(usuario: Any) -> bool:
    if getattr(usuario, "is_superuser", False):
        return True
    if nome_perfil(usuario) == NOME_ADMINISTRADOR:
        return True
    return (getattr(usuario, "role", None) or "").lower() in {"admin", "owner"} and _perfil(usuario) is None

def eh_gestor(usuario: Any) -> bool:
    if nome_perfil(usuario) == NOME_GESTOR:
        return True
    return (getattr(usuario, "role", None) or "").lower() == "gestor" and _perfil(usuario) is None

def isola_dados_usuario(usuario: Any) -> bool:
    if getattr(usuario, "is_superuser", False):
        return False
    perfil = _perfil(usuario)
    if perfil is not None:
        return bool(getattr(perfil, "isolate_data", False))
    return (getattr(usuario, "role", None) or "").lower() in {"member", "viewer", "assistant"}

def permissoes_efetivas_usuario(usuario: Any) -> list[dict]:
    if getattr(usuario, "is_superuser", False):
        return montar_permissoes(todas_true(), aplicar_limites=False)
    perfil = _perfil(usuario)
    if perfil is not None:
        return montar_permissoes_do_perfil(getattr(perfil, "name", None), getattr(perfil, "permissions", None))
    nome = nome_do_papel(getattr(usuario, "role", None))
    bruto = next((item["permissoes"] for item in PERFIS_PADRAO if item["nome"] == nome), None)
    return montar_permissoes_do_perfil(nome, bruto)

def tem_permissao_usuario(usuario: Any, modulo: str, acao: str = "visualizar") -> bool:
    if getattr(usuario, "is_superuser", False):
        return True
    perfil = _perfil(usuario)
    if perfil is not None:
        return tem_permissao(getattr(perfil, "permissions", None), modulo, acao, getattr(perfil, "name", None))
    nome = nome_do_papel(getattr(usuario, "role", None))
    bruto = next((item["permissoes"] for item in PERFIS_PADRAO if item["nome"] == nome), None)
    return tem_permissao(bruto, modulo, acao, nome)

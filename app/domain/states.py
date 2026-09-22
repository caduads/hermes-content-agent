"""Máquinas de estado do domínio (briefing seção 7).

Transições são validadas: uma mudança de estado inválida levanta InvalidTransition.
Isso protege o fluxo e é a base dos testes unitários exigidos (seção 21.1).
"""
from __future__ import annotations


class InvalidTransition(Exception):
    pass


# --- Estados da IDEIA ---
IDEA_TRANSITIONS = {
    "rascunho": {"pesquisando", "cancelada"},
    "pesquisando": {"analisando", "falha", "cancelada"},
    "analisando": {"selecionada", "falha", "cancelada"},
    "selecionada": {"roteirizando", "cancelada"},
    "roteirizando": {"produzindo", "falha", "bloqueada", "cancelada"},
    "produzindo": {"revisando", "falha", "bloqueada", "cancelada"},
    "revisando": {"entregando", "produzindo", "bloqueada", "falha", "cancelada"},
    "entregando": {"concluida", "falha"},
    "concluida": set(),
    "falha": {"pesquisando", "roteirizando", "produzindo", "cancelada"},  # retomável
    "bloqueada": {"roteirizando", "produzindo", "revisando", "cancelada"},
    "cancelada": set(),
}

# --- Estados da VARIANTE DE IDIOMA ---
VARIANT_TRANSITIONS = {
    "aguardando": {"adaptando", "falha"},
    "adaptando": {"produzindo_voz", "falha", "bloqueado"},
    "produzindo_voz": {"montando", "falha", "bloqueado"},
    "montando": {"revisando", "falha", "bloqueado"},
    "revisando": {"pronto", "adaptando", "montando", "bloqueado", "falha"},
    "pronto": set(),
    "falha": {"adaptando", "produzindo_voz", "montando"},  # retomável
    "bloqueado": {"adaptando", "montando", "revisando"},
}

IDEA_STATES = set(IDEA_TRANSITIONS)
VARIANT_STATES = set(VARIANT_TRANSITIONS)
IDEA_TERMINAL = {"concluida", "cancelada"}
VARIANT_TERMINAL = {"pronto"}


def _check(table, current, nxt, kind):
    if current not in table:
        raise InvalidTransition(f"{kind}: estado atual desconhecido '{current}'")
    if nxt not in table:
        raise InvalidTransition(f"{kind}: estado destino desconhecido '{nxt}'")
    if nxt not in table[current]:
        raise InvalidTransition(f"{kind}: transição inválida {current} -> {nxt}")
    return True


def can_transition_idea(current: str, nxt: str) -> bool:
    return nxt in IDEA_TRANSITIONS.get(current, set())


def assert_idea_transition(current: str, nxt: str) -> bool:
    return _check(IDEA_TRANSITIONS, current, nxt, "ideia")


def can_transition_variant(current: str, nxt: str) -> bool:
    return nxt in VARIANT_TRANSITIONS.get(current, set())


def assert_variant_transition(current: str, nxt: str) -> bool:
    return _check(VARIANT_TRANSITIONS, current, nxt, "variante")

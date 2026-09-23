"""Adaptador do Google Flow — CONTRATO + modo MANUAL explícito.

Regras (briefing 9.4):
- NÃO presumir que créditos do produto Flow são consumíveis pela API Veo (faturamentos distintos).
- NÃO chamar API paga. NÃO automatizar contas web sem autorização.
- Enquanto não houver via oficialmente permitida, cada geração vira uma ORDEM DE TRABALHO MANUAL
  e o job entra no estado `aguardando_operacao_flow`. Nada de vídeo real declarado sem evidência
  (arquivo presente + hash), o que é verificado depois pela validação de mídia.

Modos (env CONTENT_FLOW_MODE):
- "manual" (padrão): produz ordem de trabalho; não gera nada automaticamente.
- "api": DESABILITADO — exige decisão de gasto + autorização; levanta FlowNotAuthorized.
"""
from __future__ import annotations

import os

VEO_FAST_CREDITS_PER_GEN = 20  # projeção do briefing (não é meta)


class FlowNotAuthorized(Exception):
    pass


def mode() -> str:
    return os.environ.get("CONTENT_FLOW_MODE", "manual").strip().lower()


def estimate_credits(num_scenes: int) -> int:
    return int(num_scenes) * VEO_FAST_CREDITS_PER_GEN


def plan_scene(scene: dict) -> dict:
    """Retorna o plano de geração de UMA cena, sem gerar nada.

    scene: {"index": int, "prompt": str, "seconds": float, "no_text_overlay": bool}
    """
    m = mode()
    if m == "api":
        # Bloqueado de propósito: consumir Veo API é gasto em dólar e faturamento distinto do Flow.
        raise FlowNotAuthorized(
            "CONTENT_FLOW_MODE=api requer decisão de gasto e autorização explícita do operador; "
            "e não há prova de que os créditos do produto Flow sejam usáveis pela API Veo."
        )
    # modo manual
    return {
        "route": "manual",
        "state": "aguardando_operacao_flow",
        "estimated_credits": VEO_FAST_CREDITS_PER_GEN,
        "instructions": build_manual_work_order(scene),
    }


def build_manual_work_order(scene: dict) -> dict:
    """Ordem de trabalho para o operador gerar a cena no produto Flow (web), manualmente."""
    idx = scene.get("index", 0)
    return {
        "passo": f"Gerar cena {idx} no Google Flow (Veo Fast)",
        "prompt_sugerido": scene.get("prompt", ""),
        "duracao_alvo_seg": scene.get("seconds", 8),
        "preferencias": [
            "vertical 9:16",
            "sem texto embutido na imagem" if scene.get("no_text_overlay", True) else "texto permitido",
            "sem movimento labial dependente de idioma (reuso entre pt-BR/en/es)",
        ],
        "onde_salvar": f"o arquivo baixado deve ser informado ao sistema como cena {idx}",
        "creditos_estimados": VEO_FAST_CREDITS_PER_GEN,
        "aviso": "Reservar crédito antes; registrar o débito observado depois (usage_events).",
    }


def manual_work_order_for_variant(scene_plan: list) -> dict:
    """Consolida a ordem de trabalho manual para todas as cenas de uma variante."""
    scenes = scene_plan or []
    return {
        "modo": "manual",
        "estado": "aguardando_operacao_flow",
        "total_cenas": len(scenes),
        "creditos_estimados_total": estimate_credits(len(scenes)),
        "cenas": [build_manual_work_order(s) for s in scenes],
        "nota": "Nenhuma geração automática foi feita. Gere no Flow, baixe e informe os caminhos.",
    }

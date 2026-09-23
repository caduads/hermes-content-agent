"""Revisão técnica/editorial determinística de uma variante (briefing 6.7 / 21.3).

Não aprova uma saída só pelo modelo que a produziu: aqui são gates DETERMINÍSTICOS
(presença de áudio/legenda/vídeo, proporção 9:16, duração, legendas válidas).
O limite de 2 rodadas automáticas é aplicado pelo pipeline; aqui só avaliamos.
"""
from __future__ import annotations

from app.media import subtitles
from app.domain import media

MAX_AUTO_REVISIONS = 2


def review_variant(variant: dict, srt_text: str = "", video_probe: dict = None,
                   max_seconds: float = 95) -> dict:
    """Avalia uma variante. `variant` traz caminhos/flags; `video_probe` é saída do ffprobe (ou None).

    Retorna {ok, checks, reasons, pending}. `pending` lista o que ainda não pôde ser verificado
    (ex.: vídeo aguardando geração manual no Flow) — pendência não é reprovação.
    """
    checks, reasons, pending = {}, [], []

    # narração presente
    checks["tem_narracao"] = bool(variant.get("voice_path"))
    if not checks["tem_narracao"]:
        pending.append("narração ainda não produzida")

    # legendas válidas
    if srt_text:
        sv = subtitles.validate_srt(srt_text, max_seconds)
        checks["legendas_ok"] = sv["ok"]
        if not sv["ok"]:
            reasons += [f"legenda: {r}" for r in sv["reasons"]]
    else:
        checks["legendas_ok"] = False
        pending.append("legenda ainda não gerada")

    # vídeo (só valida se houver probe; caso contrário fica pendente — Flow manual)
    if video_probe is not None:
        ev = media.evaluate_probe(video_probe, max_seconds=max_seconds)
        checks["video_ok"] = ev["ok"]
        if not ev["ok"]:
            reasons += [f"vídeo: {r}" for r in ev["reasons"]]
    else:
        pending.append("vídeo aguardando geração (Flow manual) — não reprovado")

    # roteiro presente
    checks["tem_roteiro"] = bool(variant.get("script"))
    if not checks["tem_roteiro"]:
        reasons.append("roteiro ausente")

    ok = not reasons  # pendências não reprovam; motivos reprovam
    return {"ok": ok, "checks": checks, "reasons": reasons, "pending": pending}


def revision_allowed(revision_count: int) -> bool:
    """True se ainda há rodada automática disponível (limite 2)."""
    return revision_count < MAX_AUTO_REVISIONS

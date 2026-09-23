"""Montagem do pacote de entrega e das tags MEDIA: para o Telegram.

Só emite `MEDIA:<path>` para arquivos que EXISTEM (evidência). Um vídeo ainda não
gerado (Flow manual pendente) aparece como pendência, nunca como entregue.
"""
from __future__ import annotations

import os

# extensões que o gateway do Hermes entrega como anexo nativo (subset relevante)
DELIVERABLE = (".mp4", ".mov", ".webm", ".srt", ".vtt", ".png", ".jpg", ".jpeg",
               ".pdf", ".txt", ".md", ".zip", ".mp3", ".m4a", ".ogg")


def _exists(path):
    return bool(path) and os.path.isfile(path)


def variant_package(variant: dict) -> dict:
    """Monta o pacote de UMA variante de idioma. Retorna manifesto + linhas MEDIA + pendências."""
    fields = [
        ("video_path", "vídeo final 9:16"),
        ("caption_path", "legenda (SRT/VTT)"),
        ("thumbnail_path", "capa"),
        ("voice_path", "narração"),
    ]
    media_lines, present, missing = [], [], []
    for key, label in fields:
        p = variant.get(key)
        if _exists(p) and os.path.splitext(p)[1].lower() in DELIVERABLE:
            media_lines.append("MEDIA:" + os.path.abspath(p))
            present.append(label)
        else:
            missing.append(label)
    return {
        "locale": variant.get("locale"),
        "present": present,
        "missing": missing,
        "media_lines": media_lines,
        "ready": not missing,
    }


def idea_delivery(idea_title: str, variants: list) -> str:
    """Texto de entrega de uma ideia (3 variantes) para o Telegram, com tags MEDIA das que existem."""
    out = [f"Entrega — {idea_title}", ""]
    all_media = []
    for v in variants:
        pkg = variant_package(v)
        status = "pronto" if pkg["ready"] else ("faltando: " + ", ".join(pkg["missing"]))
        out.append(f"[{pkg['locale']}] {status}")
        all_media += pkg["media_lines"]
    out.append("")
    out += all_media  # cada MEDIA: numa linha própria — o gateway anexa os arquivos existentes
    return "\n".join(out).strip() + "\n"

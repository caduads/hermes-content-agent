"""Geração e validação de legendas (SRT/VTT) — determinística e testável.

A narração define a duração total; as falas são divididas em cues com tempos
proporcionais ao tamanho do texto. Sem dependência externa.
"""
from __future__ import annotations

import re


def _split_cues(script: str, max_chars: int = 90):
    # quebra por frases e por tamanho máximo, preservando ordem
    parts = re.split(r"(?<=[.!?…])\s+", (script or "").strip())
    cues = []
    for p in parts:
        p = p.strip()
        while len(p) > max_chars:
            cut = p.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            cues.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            cues.append(p)
    return [c for c in cues if c]


def _fmt_ts(seconds: float, vtt: bool = False):
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    sep = "." if vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def build_cues(script: str, total_seconds: float):
    """Divide o script em cues com início/fim proporcionais ao tamanho do texto."""
    cues = _split_cues(script)
    if not cues:
        return []
    total_chars = sum(len(c) for c in cues) or 1
    out = []
    t = 0.0
    for c in cues:
        dur = max(0.8, total_seconds * (len(c) / total_chars))
        out.append({"start": t, "end": t + dur, "text": c})
        t += dur
    # normaliza para casar exatamente com a duração total
    if out:
        scale = total_seconds / out[-1]["end"] if out[-1]["end"] > 0 else 1
        for cue in out:
            cue["start"] *= scale
            cue["end"] *= scale
    return out


def to_srt(script: str, total_seconds: float) -> str:
    lines = []
    for i, cue in enumerate(build_cues(script, total_seconds), 1):
        lines.append(str(i))
        lines.append(f"{_fmt_ts(cue['start'])} --> {_fmt_ts(cue['end'])}")
        lines.append(cue["text"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def to_vtt(script: str, total_seconds: float) -> str:
    body = []
    for cue in build_cues(script, total_seconds):
        body.append(f"{_fmt_ts(cue['start'], vtt=True)} --> {_fmt_ts(cue['end'], vtt=True)}")
        body.append(cue["text"])
        body.append("")
    return "WEBVTT\n\n" + "\n".join(body).strip() + "\n"


_SRT_TS = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")


def validate_srt(srt_text: str, max_seconds: float):
    """Valida SRT: cues em ordem, sem segmento fora da duração, sem tempos invertidos."""
    reasons = []
    blocks = [b for b in re.split(r"\n\s*\n", srt_text.strip()) if b.strip()]
    if not blocks:
        return {"ok": False, "reasons": ["legenda vazia"], "cues": 0}
    last_end = -1.0

    def _sec(m):
        return int(m[0]) * 3600 + int(m[1]) * 60 + int(m[2]) + int(m[3]) / 1000

    for b in blocks:
        rows = b.splitlines()
        if len(rows) < 3:
            reasons.append("bloco de legenda malformado")
            continue
        mt = re.match(r"^(.+?)\s*-->\s*(.+?)$", rows[1].strip())
        if not mt:
            reasons.append(f"timecode inválido: {rows[1]!r}")
            continue
        a, b2 = _SRT_TS.match(mt.group(1).strip()), _SRT_TS.match(mt.group(2).strip())
        if not a or not b2:
            reasons.append("formato de timecode inválido")
            continue
        start, end = _sec(a.groups()), _sec(b2.groups())
        if end <= start:
            reasons.append("cue com fim <= início")
        if end > max_seconds + 0.5:
            reasons.append(f"cue além da duração ({end:.1f}s > {max_seconds:.1f}s)")
        if start < last_end - 0.01:
            reasons.append("cues fora de ordem/sobrepostos")
        last_end = end
    return {"ok": not reasons, "reasons": reasons, "cues": len(blocks)}

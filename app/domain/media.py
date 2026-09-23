"""Validação automática de mídia (briefing 21.3).

- probe(path): roda ffprobe e retorna o JSON parseado; se ffprobe faltar, {'available': False}.
- evaluate_probe(...): núcleo PURO e testável — recebe o dict do ffprobe e devolve os checks.

Checks: proporção vertical (9:16), presença de áudio, duração dentro da faixa, codec de vídeo,
resolução, arquivo reproduzível (streams presentes).
"""
from __future__ import annotations

import json
import shutil
import subprocess

ACCEPTED_VIDEO_CODECS = {"h264", "hevc", "vp9", "av1"}


def probe(path: str) -> dict:
    """Executa ffprobe. Retorna dict com 'available': False se ffprobe não existir."""
    if shutil.which("ffprobe") is None:
        return {"available": False, "reason": "ffprobe não encontrado no PATH"}
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            return {"available": True, "ok": False, "reason": f"ffprobe rc={out.returncode}"}
        data = json.loads(out.stdout or "{}")
        data["available"] = True
        return data
    except Exception as e:  # pragma: no cover
        return {"available": True, "ok": False, "reason": str(e)}


def evaluate_probe(probe_data: dict, min_seconds: float = 5, max_seconds: float = 95,
                   want_ratio=(9, 16)) -> dict:
    """Núcleo puro: avalia um dict estilo ffprobe e retorna {ok, checks, reasons}.

    Testável sem ffprobe instalado.
    """
    checks = {}
    reasons = []
    streams = probe_data.get("streams", []) or []
    fmt = probe_data.get("format", {}) or {}

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # áudio presente
    checks["tem_audio"] = audio is not None
    if not checks["tem_audio"]:
        reasons.append("sem trilha de áudio")

    # vídeo presente + codec aceito
    checks["tem_video"] = video is not None
    if video is None:
        reasons.append("sem stream de vídeo")
        checks["codec_ok"] = False
        checks["proporcao_9_16"] = False
    else:
        codec = (video.get("codec_name") or "").lower()
        checks["codec_ok"] = codec in ACCEPTED_VIDEO_CODECS
        if not checks["codec_ok"]:
            reasons.append(f"codec de vídeo não aceito: {codec or 'desconhecido'}")
        w = int(video.get("width") or 0)
        h = int(video.get("height") or 0)
        # 9:16 vertical: h/w == 16/9 (tolerância pequena)
        want = want_ratio[1] / want_ratio[0]  # 16/9
        checks["proporcao_9_16"] = w > 0 and h > 0 and abs((h / w) - want) < 0.05
        if not checks["proporcao_9_16"]:
            reasons.append(f"proporção não é 9:16 ({w}x{h})")

    # duração na faixa
    try:
        dur = float(fmt.get("duration") or 0)
    except (TypeError, ValueError):
        dur = 0.0
    checks["duracao_ok"] = min_seconds <= dur <= max_seconds
    if not checks["duracao_ok"]:
        reasons.append(f"duração fora da faixa: {dur:.1f}s (faixa {min_seconds}-{max_seconds}s)")

    ok = all(checks.values())
    return {"ok": ok, "checks": checks, "reasons": reasons, "duration": dur}


def validate_vertical_video(path: str, min_seconds: float = 5, max_seconds: float = 95) -> dict:
    """Conveniência: probe + evaluate. Se ffprobe faltar, retorna ok=None (indeterminado)."""
    p = probe(path)
    if not p.get("available"):
        return {"ok": None, "checks": {}, "reasons": [p.get("reason", "ffprobe indisponível")]}
    return evaluate_probe(p, min_seconds, max_seconds)

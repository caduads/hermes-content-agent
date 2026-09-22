"""Helpers de identidade, idempotência e redação de segredos.

- new_id(): id único curto para entidades.
- input_hash(): hash estável de uma entrada de job (idempotência).
- redact(): remove segredos de textos antes de logar.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid

# Padrões de segredo redigidos em logs (token Telegram, chaves, bearer, cookies).
_SECRET_PATTERNS = [
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b"),          # token de bot Telegram
    re.compile(r"\bsk-[A-Za-z0-9-]{16,}\b"),                # chaves estilo OpenAI/OpenRouter
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}\b"),    # Authorization: Bearer
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|cookie)\b\s*[=:]\s*\S+"),
]


def new_id(prefix: str = "") -> str:
    """Id único e curto. Ex.: new_id('idea') -> 'idea_ab12cd34'."""
    short = uuid.uuid4().hex[:8]
    return f"{prefix}_{short}" if prefix else short


def input_hash(payload) -> str:
    """Hash determinístico de uma entrada (dict/list/str) para idempotência de jobs.

    Duas chamadas com a mesma entrada semântica produzem o mesmo hash, então o
    coordenador pode detectar 'esse trabalho já foi feito' antes de repetir.
    """
    if isinstance(payload, (dict, list)):
        material = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    else:
        material = str(payload)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    """SHA-256 de um arquivo (para a tabela artifacts)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def redact(text: str) -> str:
    """Remove segredos de um texto antes de gravar em log. Nunca logar cru."""
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out

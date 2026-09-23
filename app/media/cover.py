"""Geração DETERMINÍSTICA de capa (SVG 9:16) e metadados de uma variante.

Sem LLM e sem gasto: produz uma capa real (arquivo com hash, entregável) e um bloco de
metadados-base a partir do título/roteiro/locale. A REDAÇÃO editorial real (título/hashtags
localizados de verdade) ainda depende do LLM — aqui é uma base estrutural honesta, não conteúdo
inventado; o texto é derivado do que já existe (título da ideia e roteiro).
"""
from __future__ import annotations

import json
import os
import re

from app.domain import ids

W, H = 1080, 1920  # 9:16

_LOCALE_LABEL = {"pt-BR": "PT-BR", "en": "EN", "es": "ES"}


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap(text: str, width: int):
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:5]


def build_cover_svg(title: str, hook: str, locale: str) -> str:
    label = _LOCALE_LABEL.get(locale, (locale or "").upper())
    title_lines = _wrap(title, 18)
    hook_lines = _wrap(hook, 30)
    ty = 760
    title_spans = "".join(
        f'<tspan x="90" dy="{0 if i == 0 else 120}">{_esc(l)}</tspan>' for i, l in enumerate(title_lines))
    hook_spans = "".join(
        f'<tspan x="90" dy="{0 if i == 0 else 64}">{_esc(l)}</tspan>' for i, l in enumerate(hook_lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0f172a"/><stop offset="1" stop-color="#1e293b"/></linearGradient></defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <rect x="90" y="120" width="180" height="64" rx="12" fill="#22d3ee"/>
  <text x="120" y="165" font-family="Arial, sans-serif" font-size="36" font-weight="700" fill="#0f172a">{_esc(label)}</text>
  <text y="{ty}" font-family="Arial, sans-serif" font-size="96" font-weight="800" fill="#f8fafc">{title_spans}</text>
  <rect x="90" y="{ty + 160}" width="900" height="6" fill="#22d3ee"/>
  <text y="{ty + 260}" font-family="Arial, sans-serif" font-size="46" fill="#cbd5e1">{hook_spans}</text>
  <text x="90" y="{H - 90}" font-family="Arial, sans-serif" font-size="34" fill="#64748b">content-agent · 9:16 · placeholder de capa (localizacao real pende do LLM)</text>
</svg>'''


def build_metadata(title: str, script: str, locale: str, target_seconds: float) -> dict:
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", (title or ""))
    tags = ["#" + w.lower() for w in words if len(w) > 3][:5] or ["#shorts"]
    desc = re.sub(r"\s+", " ", (script or "")).strip()[:180]
    return {
        "locale": locale,
        "titulo_base": title,
        "descricao_base": desc,
        "hashtags_base": tags,
        "formato": "9:16",
        "duracao_alvo_seg": target_seconds,
        "origem": "derivado de titulo/roteiro (sem LLM) — adaptacao editorial real pende do LLM",
    }


def render_assets(conn, variant_id, out_dir, target_seconds=45) -> dict:
    """Gera capa SVG + metadados para a variante, grava thumbnail_path/metadata_json e registra artefato."""
    v = dict(conn.execute("SELECT * FROM language_variants WHERE id=?", (variant_id,)).fetchone())
    idea = conn.execute("SELECT id, title FROM ideas WHERE id=?", (v["idea_id"],)).fetchone()
    title = idea["title"] if idea else variant_id
    script = v.get("script") or ""
    hook = re.split(r"[.!?]", script, 1)[0].strip() if script else title
    os.makedirs(out_dir, exist_ok=True)
    svg = build_cover_svg(title, hook, v["locale"])
    cover_path = os.path.join(out_dir, f"capa_{v['locale']}.svg")
    with open(cover_path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    meta = build_metadata(title, script, v["locale"], target_seconds)
    conn.execute("UPDATE language_variants SET thumbnail_path=?, metadata_json=? WHERE id=?",
                 (cover_path, json.dumps(meta, ensure_ascii=False), variant_id))
    sha = ids.sha256_file(cover_path)
    conn.execute(
        "INSERT INTO artifacts(id,idea_id,variant_id,artifact_type,path,sha256,size_bytes,metadata_json) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (ids.new_id("art"), v["idea_id"], variant_id, "cover", cover_path, sha,
         os.path.getsize(cover_path), json.dumps(meta, ensure_ascii=False)))
    conn.commit()
    return {"cover_path": cover_path, "metadata": meta}

"""Runner do piloto (Fase C) + relatório da Fase D.

Cria 2 ideias do mesmo nicho (1 educativa, 1 comercial), inicializa as 3 variantes de idioma
por ideia (6 no total) e roda o pipeline de produção em cada uma. Com os backends padrão
(sem LLM vivo, Flow manual), cada variante avança até o ponto do vídeo e permanece em
`revisando` com o vídeo em `aguardando_operacao_flow` — NUNCA declara vídeo pronto sem arquivo.

Duas dependências reais ficam explícitas no relatório: execução viva do LLM (localização/roteiro)
e operação manual do Flow (vídeo).
"""
from __future__ import annotations

import time

from app.persistence import repo
from app.media import pipeline

LOCALES = ("pt-BR", "en", "es")

# Roteiros-base ESTRUTURAIS de piloto (placeholders honestos: a redação/adaptação real
# depende do LLM vivo; aqui servem para exercitar o pipeline de ponta a ponta).
EDU_BASE = ("Gancho: 3 ajustes que economizam 1 hora por dia. "
            "Desenvolvimento: cada ajuste com um exemplo. Conclusao: chamada para salvar o video.")
COM_BASE = ("Gancho: a ferramenta que organiza sua casa em minutos. "
            "Demonstracao: antes e depois. Conclusao: link de afiliado autorizado, se houver.")


def _prep_idea(conn, title, objective, base_script):
    iid = repo.idea_add(conn, title, objective=objective)
    conn.execute("UPDATE ideas SET base_script=? WHERE id=?", (base_script, iid)); conn.commit()
    for st in ("pesquisando", "analisando", "selecionada", "roteirizando", "produzindo"):
        repo.idea_transition(conn, iid, st)
    created = dict(repo.variants_init(conn, iid))
    for loc, vid in created.items():
        # placeholder honesto por idioma — adaptacao real pende do LLM
        script = f"[{loc}] (localizacao real pende do LLM Nemotron) {base_script}"
        conn.execute("UPDATE language_variants SET script=? WHERE id=?", (script, vid)); conn.commit()
    return iid, created


def run_pilot(conn, niche_name="ferramentas digitais", artifacts_root=None, target_seconds=45):
    t0 = time.time()
    nid = repo.niche_add(conn, niche_name, "nicho hipotese do piloto")
    edu_id, edu_vars = _prep_idea(conn, "3 ajustes que economizam 1h/dia", "educacao", EDU_BASE)
    com_id, com_vars = _prep_idea(conn, "Organize a casa em minutos", "acao_comercial", COM_BASE)
    conn.execute("UPDATE ideas SET niche_id=? WHERE id IN (?,?)", (nid, edu_id, com_id)); conn.commit()

    results = []
    for iid, vmap in ((edu_id, edu_vars), (com_id, com_vars)):
        for loc, vid in vmap.items():
            adir = None
            if artifacts_root:
                import os
                adir = os.path.join(artifacts_root, vid)
            rep = pipeline.produce_variant(conn, vid, target_seconds=target_seconds, artifacts_dir=adir)
            results.append(rep)
    elapsed = time.time() - t0
    return {"niche_id": nid, "idea_edu": edu_id, "idea_com": com_id,
            "variants": results, "elapsed_seconds": round(elapsed, 2)}


def phase_d_report(conn) -> dict:
    """Relatório da Fase D: autonomia, custo, evidências, pendências e as 2 dependências reais."""
    ideas = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
    variants = [dict(r) for r in conn.execute("SELECT * FROM language_variants").fetchall()]
    nready = sum(1 for v in variants if v["status"] == "pronto")
    nvideos = conn.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type='video'").fetchone()[0]
    ncaptions = conn.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type='caption'").fetchone()[0]
    jobs_total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    jobs_ok = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='concluido'").fetchone()[0]
    jobs_fail = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='falha'").fetchone()[0]
    est, act = conn.execute("SELECT COALESCE(SUM(estimated_amount),0), COALESCE(SUM(actual_amount),0) FROM usage_events").fetchone()
    blocked = sum(1 for v in variants if v["status"] == "bloqueado")
    pending_video = sum(1 for v in variants if not v["video_path"])
    # autonomia: fracao de jobs concluidos sem falha (proxy operacional; nao mede qualidade editorial)
    autonomy = round(100 * jobs_ok / jobs_total, 1) if jobs_total else 0.0
    return {
        "ideias": ideas,
        "variantes_total": len(variants),
        "variantes_prontas": nready,
        "videos_reais": nvideos,          # so conta arquivo real com hash
        "legendas_geradas": ncaptions,
        "jobs": {"total": jobs_total, "ok": jobs_ok, "falha": jobs_fail},
        "autonomia_operacional_pct": autonomy,
        "custo": {"estimado": est, "real": act, "moeda": "BRL/creditos"},
        "variantes_bloqueadas": blocked,
        "variantes_com_video_pendente": pending_video,
        "dependencias_reais_restantes": [
            "execucao viva do LLM (Nemotron) para pesquisa/roteiro/localizacao",
            "operacao manual do Google Flow para o video real (aguardando_operacao_flow)",
        ],
        "nota": "Autonomia aqui e operacional (pipeline), nao mede sucesso editorial nem financeiro. "
                "videos_reais so aumenta quando um arquivo de video existir e for validado.",
    }

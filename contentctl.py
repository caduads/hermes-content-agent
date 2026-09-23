"""contentctl — CLI de controle do content-agent.

Uso:
  python contentctl.py db-init [--db PATH]     # aplica migrations
  python contentctl.py db-check [--db PATH]    # lista tabelas e versão de schema
  python contentctl.py healthcheck [--db PATH] # verificações operacionais básicas
  python contentctl.py selftest                # roda os testes unitários

As skills do Hermes chamam este CLI; nada de lógica de negócio vive só no chat.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.persistence import db as dbmod  # noqa: E402
from app.persistence import repo  # noqa: E402
from app.domain import states  # noqa: E402
from app.media import pipeline as media_pipeline  # noqa: E402
from app.media import delivery as media_delivery  # noqa: E402
from app.media import flow as media_flow  # noqa: E402
from app import pilot as pilot_mod  # noqa: E402

DEFAULT_DB = os.environ.get("CONTENT_DB_PATH", os.path.join(REPO_ROOT, "data", "db", "content.db"))


def cmd_db_init(args):
    conn = dbmod.connect(args.db)
    applied = dbmod.migrate(conn)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print(f"DB: {args.db}")
    print(f"Migrations aplicadas agora: {applied or 'nenhuma (já atualizado)'}")
    print(f"Tabelas ({len(tables)}): {', '.join(tables)}")
    conn.close()


def cmd_db_check(args):
    conn = dbmod.connect(args.db)
    ver = conn.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()[0]
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print(f"schema_version={ver} tabelas={len(tables)}")
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} linhas")
    conn.close()


def cmd_healthcheck(args):
    ok = True
    # banco acessível + schema aplicado
    try:
        conn = dbmod.connect(args.db)
        ver = conn.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()[0]
        conn.close()
        print(f"[ok] banco acessível, schema v{ver}")
        if ver < 1:
            ok = False
            print("[erro] schema não aplicado (rode db-init)")
    except Exception as e:
        ok = False
        print(f"[erro] banco: {e}")
    print("RESULT:", "OK" if ok else "FALHA")
    sys.exit(0 if ok else 1)


def _counts_by_status(conn, table):
    rows = conn.execute(f"SELECT status, COUNT(*) c FROM {table} GROUP BY status").fetchall()
    return {r[0]: r[1] for r in rows}


def cmd_status(args):
    """Resumo operacional do Coordenador (briefing 6.1), lido do banco."""
    conn = dbmod.connect(args.db)
    ideas = _counts_by_status(conn, "ideas")
    variants = _counts_by_status(conn, "language_variants")
    jobs = _counts_by_status(conn, "jobs")
    niches = _counts_by_status(conn, "niches")
    est = conn.execute("SELECT COALESCE(SUM(estimated_amount),0), COALESCE(SUM(actual_amount),0) FROM usage_events").fetchone()
    failed = (jobs.get("falha", 0) + ideas.get("falha", 0) + variants.get("falha", 0))
    print("=== STATUS content-agent ===")
    print(f"nichos: {niches or 'nenhum'}")
    print(f"ideias: {ideas or 'nenhuma'}")
    print(f"variantes: {variants or 'nenhuma'}")
    print(f"jobs: {jobs or 'nenhum'}")
    print(f"custo estimado/real: {est[0]:.2f} / {est[1]:.2f}")
    print(f"itens com falha: {failed}")
    if not ideas and not niches:
        print("proxima acao: rodar /pesquisar_nichos (nenhuma ideia ou nicho ainda)")
    else:
        pend = [s for s in ("selecionada", "roteirizando", "produzindo", "revisando") if ideas.get(s)]
        print("proxima acao:", ("processar ideias em " + ", ".join(pend)) if pend else "aguardando novas tarefas")
    conn.close()


def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False))


def cmd_niche_add(args):
    conn = dbmod.connect(args.db)
    _emit({"niche_id": repo.niche_add(conn, args.name, args.description or "")})
    conn.close()


def cmd_niche_score(args):
    conn = dbmod.connect(args.db)
    repo.niche_score(conn, args.id, args.audience, args.commercial, args.feasibility, args.confidence, args.evidence or "")
    _emit({"ok": True, "niche_id": args.id})
    conn.close()


def cmd_source_add(args):
    conn = dbmod.connect(args.db)
    metrics = json.loads(args.metrics) if args.metrics else {}
    sid, created = repo.source_add(conn, args.url, args.platform or "", args.creator or "",
                                   args.published_at, args.language or "", metrics,
                                   args.summary or "", args.limitations or "")
    _emit({"source_id": sid, "created": created})
    conn.close()


def cmd_idea_add(args):
    conn = dbmod.connect(args.db)
    _emit({"idea_id": repo.idea_add(conn, args.title, args.niche, args.objective or "",
                                    args.audience or "", args.hypothesis or "")})
    conn.close()


def cmd_idea_transition(args):
    conn = dbmod.connect(args.db)
    try:
        repo.idea_transition(conn, args.id, args.to)
        _emit({"ok": True, "idea_id": args.id, "status": args.to})
    except states.InvalidTransition as e:
        _emit({"ok": False, "error": str(e)})
    conn.close()


def cmd_idea_attach_source(args):
    conn = dbmod.connect(args.db)
    repo.idea_attach_source(conn, args.idea, args.source, args.note or "")
    _emit({"ok": True})
    conn.close()


def cmd_variants_init(args):
    conn = dbmod.connect(args.db)
    _emit({"created": repo.variants_init(conn, args.idea)})
    conn.close()


def cmd_variant_transition(args):
    conn = dbmod.connect(args.db)
    try:
        repo.variant_transition(conn, args.id, args.to)
        _emit({"ok": True, "variant_id": args.id, "status": args.to})
    except states.InvalidTransition as e:
        _emit({"ok": False, "error": str(e)})
    conn.close()


def cmd_job_start(args):
    conn = dbmod.connect(args.db)
    payload = json.loads(args.payload) if args.payload else {}
    jid, created = repo.job_start(conn, args.type, args.idea, args.variant, args.provider, payload)
    _emit({"job_id": jid, "created": created})
    conn.close()


def cmd_job_finish(args):
    conn = dbmod.connect(args.db)
    repo.job_finish(conn, args.id, ok=(not args.failed), error_code=args.error_code, error_message=args.error_message)
    _emit({"ok": True, "job_id": args.id})
    conn.close()


def cmd_usage_add(args):
    conn = dbmod.connect(args.db)
    repo.usage_add(conn, args.account, args.job, args.unit, args.estimated, args.actual, args.currency or "")
    _emit({"ok": True})
    conn.close()


def cmd_list(args):
    conn = dbmod.connect(args.db)
    table = {"niches": "niches", "ideas": "ideas", "sources": "sources",
             "variants": "language_variants", "jobs": "jobs"}[args.entity]
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?", (args.limit,)).fetchall()
    _emit([dict(r) for r in rows])
    conn.close()


def cmd_produce(args):
    conn = dbmod.connect(args.db)
    rep = media_pipeline.produce_variant(conn, args.variant, target_seconds=args.seconds,
                                         artifacts_dir=args.artifacts_dir)
    _emit(rep)
    conn.close()


def cmd_deliver(args):
    conn = dbmod.connect(args.db)
    idea = conn.execute("SELECT title FROM ideas WHERE id=?", (args.idea,)).fetchone()
    variants = [dict(r) for r in conn.execute(
        "SELECT * FROM language_variants WHERE idea_id=? ORDER BY locale", (args.idea,)).fetchall()]
    print(media_delivery.idea_delivery(idea[0] if idea else args.idea, variants))
    conn.close()


def cmd_flow_order(args):
    # Ordem de trabalho manual do Flow para uma variante (sem gerar nada, sem gasto).
    _emit(media_flow.manual_work_order_for_variant([]))


def cmd_pilot(args):
    conn = dbmod.connect(args.db)
    _emit(pilot_mod.run_pilot(conn, artifacts_root=args.artifacts_dir, target_seconds=args.seconds))
    conn.close()


def cmd_report(args):
    conn = dbmod.connect(args.db)
    _emit(pilot_mod.phase_d_report(conn))
    conn.close()


def cmd_selftest(args):
    from tests import run_tests
    sys.exit(0 if run_tests.main() else 1)


def build_parser():
    p = argparse.ArgumentParser(prog="contentctl")
    sub = p.add_subparsers(dest="cmd", required=True)

    # comandos com apenas --db
    for name, fn in [("db-init", cmd_db_init), ("db-check", cmd_db_check),
                     ("healthcheck", cmd_healthcheck), ("status", cmd_status)]:
        sp = sub.add_parser(name); sp.add_argument("--db", default=DEFAULT_DB); sp.set_defaults(func=fn)

    def v(name, fn):
        sp = sub.add_parser(name); sp.add_argument("--db", default=DEFAULT_DB); sp.set_defaults(func=fn)
        return sp

    sp = v("niche-add", cmd_niche_add); sp.add_argument("--name", required=True); sp.add_argument("--description")
    sp = v("niche-score", cmd_niche_score); sp.add_argument("--id", required=True)
    for a in ("audience", "commercial", "feasibility", "confidence"):
        sp.add_argument("--" + a, type=float)
    sp.add_argument("--evidence")
    sp = v("source-add", cmd_source_add); sp.add_argument("--url", required=True)
    for a in ("platform", "creator", "published-at", "language", "metrics", "summary", "limitations"):
        sp.add_argument("--" + a, dest=a.replace("-", "_"))
    sp = v("idea-add", cmd_idea_add); sp.add_argument("--title", required=True)
    sp.add_argument("--niche"); sp.add_argument("--objective"); sp.add_argument("--audience"); sp.add_argument("--hypothesis")
    sp = v("idea-transition", cmd_idea_transition); sp.add_argument("--id", required=True); sp.add_argument("--to", required=True)
    sp = v("idea-attach-source", cmd_idea_attach_source); sp.add_argument("--idea", required=True); sp.add_argument("--source", required=True); sp.add_argument("--note")
    sp = v("variants-init", cmd_variants_init); sp.add_argument("--idea", required=True)
    sp = v("variant-transition", cmd_variant_transition); sp.add_argument("--id", required=True); sp.add_argument("--to", required=True)
    sp = v("job-start", cmd_job_start); sp.add_argument("--type", required=True)
    sp.add_argument("--idea"); sp.add_argument("--variant"); sp.add_argument("--provider"); sp.add_argument("--payload")
    sp = v("job-finish", cmd_job_finish); sp.add_argument("--id", required=True); sp.add_argument("--failed", action="store_true")
    sp.add_argument("--error-code", dest="error_code"); sp.add_argument("--error-message", dest="error_message")
    sp = v("usage-add", cmd_usage_add); sp.add_argument("--account"); sp.add_argument("--job")
    sp.add_argument("--unit", default="credito"); sp.add_argument("--estimated", type=float, default=0.0)
    sp.add_argument("--actual", type=float, default=0.0); sp.add_argument("--currency")
    sp = v("list", cmd_list); sp.add_argument("--entity", required=True, choices=["niches", "ideas", "sources", "variants", "jobs"])
    sp.add_argument("--limit", type=int, default=10)
    sp = v("produce", cmd_produce); sp.add_argument("--variant", required=True)
    sp.add_argument("--seconds", type=float, default=45); sp.add_argument("--artifacts-dir", dest="artifacts_dir")
    sp = v("deliver", cmd_deliver); sp.add_argument("--idea", required=True)
    sp = v("flow-order", cmd_flow_order)
    sp = v("pilot", cmd_pilot); sp.add_argument("--seconds", type=float, default=45); sp.add_argument("--artifacts-dir", dest="artifacts_dir")
    sp = v("report", cmd_report)

    sp = sub.add_parser("selftest"); sp.set_defaults(func=cmd_selftest)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)

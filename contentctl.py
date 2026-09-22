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
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.persistence import db as dbmod  # noqa: E402

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


def cmd_selftest(args):
    from tests import run_tests
    sys.exit(0 if run_tests.main() else 1)


def build_parser():
    p = argparse.ArgumentParser(prog="contentctl")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [("db-init", cmd_db_init), ("db-check", cmd_db_check), ("healthcheck", cmd_healthcheck)]:
        sp = sub.add_parser(name)
        sp.add_argument("--db", default=DEFAULT_DB)
        sp.set_defaults(func=fn)
    sp = sub.add_parser("selftest")
    sp.set_defaults(func=cmd_selftest)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)

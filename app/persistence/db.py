"""Camada de persistência (SQLite) do content-agent.

- connect(): abre o banco com foreign_keys ON.
- migrate(): aplica as migrations em migrations/*.sql em ordem, idempotente.
- reserve_quota()/consume_quota(): reserva/consumo transacional de cota (seção 4.4/9.2).

O banco de DOMÍNIO fica separado do state.db nativo do Hermes.
"""
from __future__ import annotations

import glob
import os
import sqlite3

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_DIR = os.path.join(REPO_ROOT, "migrations")


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _applied_versions(conn) -> set:
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        return {r[0] for r in rows}
    except sqlite3.OperationalError:
        return set()


def migrate(conn) -> list:
    """Aplica todas as migrations .sql ainda não aplicadas. Retorna as versões aplicadas agora."""
    files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    applied_now = []
    for path in files:
        name = os.path.basename(path)
        try:
            version = int(name.split("_", 1)[0])
        except ValueError:
            continue
        if version in _applied_versions(conn):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            sql = fh.read()
        with conn:  # transação
            conn.executescript(sql)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (version,)
            )
        applied_now.append(version)
    return applied_now


def reserve_quota(conn, provider_account_id: str, amount: float) -> bool:
    """Reserva `amount` de cota se houver saldo observado suficiente. Transacional.

    Impede agendar geração sem saldo (briefing 9.2). Retorna True se reservou.
    """
    with conn:
        row = conn.execute(
            "SELECT quota_remaining_observed, quota_reserved FROM provider_accounts WHERE id=?",
            (provider_account_id,),
        ).fetchone()
        if row is None:
            return False
        remaining = row["quota_remaining_observed"] or 0
        reserved = row["quota_reserved"] or 0
        if (remaining - reserved) < amount:
            return False
        conn.execute(
            "UPDATE provider_accounts SET quota_reserved = ? WHERE id = ?",
            (reserved + amount, provider_account_id),
        )
    return True


def consume_quota(conn, provider_account_id: str, reserved_amount: float, actual_amount: float) -> None:
    """Confirma o consumo: libera a reserva e debita o observado real. Transacional."""
    with conn:
        row = conn.execute(
            "SELECT quota_remaining_observed, quota_reserved FROM provider_accounts WHERE id=?",
            (provider_account_id,),
        ).fetchone()
        if row is None:
            return
        remaining = row["quota_remaining_observed"] or 0
        reserved = row["quota_reserved"] or 0
        conn.execute(
            "UPDATE provider_accounts SET quota_reserved = ?, quota_remaining_observed = ? WHERE id = ?",
            (max(0.0, reserved - reserved_amount), max(0.0, remaining - actual_amount), provider_account_id),
        )

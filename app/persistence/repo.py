"""Operações de domínio do content-agent (a "camada de aplicação").

As skills chamam estas funções (via contentctl) para criar/ler/atualizar estado.
Regras do briefing embutidas: transições validadas, idempotência por input_hash,
dedup de fontes por content_hash, registro de auditoria e de uso/custo.
"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.domain import ids, states  # noqa: E402

LOCALES = ("pt-BR", "en", "es")


def _now(conn):
    return conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%SZ','now')").fetchone()[0]


def audit(conn, entity_type, entity_id, event_type, actor="coordinator", details=None):
    conn.execute(
        "INSERT INTO audit_events(id,entity_type,entity_id,event_type,actor,details_json)"
        " VALUES (?,?,?,?,?,?)",
        (ids.new_id("ev"), entity_type, entity_id, event_type, actor,
         json.dumps(details or {}, ensure_ascii=False)),
    )


# ---------- niches ----------
def niche_add(conn, name, description=""):
    nid = ids.new_id("niche")
    with conn:
        conn.execute("INSERT INTO niches(id,name,description) VALUES (?,?,?)", (nid, name, description))
        audit(conn, "niche", nid, "created", details={"name": name})
    return nid


def niche_score(conn, nid, audience=None, commercial=None, feasibility=None, confidence=None, evidence=""):
    with conn:
        conn.execute(
            "UPDATE niches SET audience_score=COALESCE(?,audience_score),"
            " commercial_score=COALESCE(?,commercial_score), feasibility_score=COALESCE(?,feasibility_score),"
            " confidence_score=COALESCE(?,confidence_score), evidence_summary=COALESCE(NULLIF(?,''),evidence_summary),"
            " status='analisando', updated_at=? WHERE id=?",
            (audience, commercial, feasibility, confidence, evidence, _now(conn), nid))
        audit(conn, "niche", nid, "scored")


# ---------- sources ----------
def source_add(conn, url, platform="", creator="", published_at=None, language="",
               metrics=None, summary="", limitations=""):
    chash = ids.input_hash(url.strip().lower())
    existing = conn.execute("SELECT id FROM sources WHERE content_hash=?", (chash,)).fetchone()
    if existing:
        return existing[0], False  # dedup: não reinsere
    sid = ids.new_id("src")
    with conn:
        conn.execute(
            "INSERT INTO sources(id,url,platform,creator,published_at,language,metrics_json,summary,limitations,content_hash)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, url, platform, creator, published_at, language,
             json.dumps(metrics or {}, ensure_ascii=False), summary, limitations, chash))
    return sid, True


# ---------- ideas ----------
def idea_add(conn, title, niche_id=None, objective="", audience="", hypothesis=""):
    iid = ids.new_id("idea")
    with conn:
        conn.execute(
            "INSERT INTO ideas(id,niche_id,title,objective,audience,hypothesis) VALUES (?,?,?,?,?,?)",
            (iid, niche_id, title, objective, audience, hypothesis))
        audit(conn, "idea", iid, "created", details={"title": title})
    return iid


def idea_transition(conn, iid, new_status):
    row = conn.execute("SELECT status FROM ideas WHERE id=?", (iid,)).fetchone()
    if row is None:
        raise ValueError(f"ideia {iid} não existe")
    states.assert_idea_transition(row[0], new_status)  # levanta InvalidTransition se inválida
    with conn:
        conn.execute("UPDATE ideas SET status=?, updated_at=? WHERE id=?", (new_status, _now(conn), iid))
        audit(conn, "idea", iid, "transition", details={"from": row[0], "to": new_status})
    return True


def idea_attach_source(conn, iid, sid, usage_note=""):
    with conn:
        conn.execute("INSERT OR IGNORE INTO idea_sources(idea_id,source_id,usage_note) VALUES (?,?,?)",
                     (iid, sid, usage_note))


# ---------- language variants ----------
def variants_init(conn, iid):
    """Cria as 3 variantes (pt-BR/en/es) da ideia, se ainda não existirem."""
    created = []
    with conn:
        for loc in LOCALES:
            exists = conn.execute("SELECT 1 FROM language_variants WHERE idea_id=? AND locale=?", (iid, loc)).fetchone()
            if exists:
                continue
            vid = ids.new_id("var")
            conn.execute("INSERT INTO language_variants(id,idea_id,locale,status) VALUES (?,?,?, 'aguardando')",
                         (vid, iid, loc))
            created.append((loc, vid))
        audit(conn, "idea", iid, "variants_init", details={"created": [c[0] for c in created]})
    return created


def variant_transition(conn, vid, new_status):
    row = conn.execute("SELECT status FROM language_variants WHERE id=?", (vid,)).fetchone()
    if row is None:
        raise ValueError(f"variante {vid} não existe")
    states.assert_variant_transition(row[0], new_status)
    with conn:
        conn.execute("UPDATE language_variants SET status=? WHERE id=?", (new_status, vid))
        audit(conn, "variant", vid, "transition", details={"from": row[0], "to": new_status})
    return True


# ---------- jobs (idempotentes) ----------
def job_start(conn, job_type, idea_id=None, variant_id=None, provider=None, input_payload=None, max_attempts=3):
    """Cria/retoma um job. Idempotente por input_hash: se já existe, devolve o existente."""
    ihash = ids.input_hash({"t": job_type, "i": idea_id, "v": variant_id, "p": input_payload or {}})
    row = conn.execute("SELECT id,status FROM jobs WHERE input_hash=?", (ihash,)).fetchone()
    if row:
        return row[0], False  # já existe: não duplica trabalho
    jid = ids.new_id("job")
    with conn:
        conn.execute(
            "INSERT INTO jobs(id,idea_id,variant_id,job_type,status,attempt,max_attempts,provider,input_hash,started_at)"
            " VALUES (?,?,?,?, 'executando', 1, ?, ?, ?, ?)",
            (jid, idea_id, variant_id, job_type, max_attempts, provider, ihash, _now(conn)))
    return jid, True


def job_finish(conn, jid, ok=True, error_code=None, error_message=None):
    with conn:
        conn.execute(
            "UPDATE jobs SET status=?, finished_at=?, error_code=?, error_message=? WHERE id=?",
            ("concluido" if ok else "falha", _now(conn), error_code,
             ids.redact(error_message) if error_message else None, jid))


# ---------- uso / custo ----------
def usage_add(conn, provider_account_id=None, job_id=None, unit="credito",
              estimated=0.0, actual=0.0, currency="", meta=None):
    with conn:
        conn.execute(
            "INSERT INTO usage_events(id,provider_account_id,job_id,unit,estimated_amount,actual_amount,currency,metadata_json)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (ids.new_id("use"), provider_account_id, job_id, unit, estimated, actual, currency,
             json.dumps(meta or {}, ensure_ascii=False)))

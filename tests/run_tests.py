"""Testes unitários essenciais (briefing 21.1), runnable sem pytest.

Rode: python tests/run_tests.py   (ou: python contentctl.py selftest)
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.domain import states, ids  # noqa: E402
from app.persistence import db as dbmod  # noqa: E402

_failures = []


def check(cond, msg):
    if cond:
        print(f"  [ok] {msg}")
    else:
        print(f"  [FALHA] {msg}")
        _failures.append(msg)


def test_state_transitions():
    print("test_state_transitions")
    check(states.can_transition_idea("rascunho", "pesquisando"), "ideia rascunho->pesquisando válida")
    check(not states.can_transition_idea("rascunho", "concluida"), "ideia rascunho->concluida inválida")
    check(states.can_transition_idea("falha", "roteirizando"), "ideia falha->roteirizando (retomável)")
    try:
        states.assert_idea_transition("concluida", "pesquisando")
        check(False, "concluida é terminal (deveria levantar)")
    except states.InvalidTransition:
        check(True, "concluida é terminal (levantou InvalidTransition)")
    check(states.can_transition_variant("adaptando", "produzindo_voz"), "variante adaptando->produzindo_voz")
    check(not states.can_transition_variant("pronto", "montando"), "variante pronto é terminal")


def test_idempotency():
    print("test_idempotency")
    a = ids.input_hash({"type": "voz", "locale": "pt-BR", "text": "olá"})
    b = ids.input_hash({"text": "olá", "locale": "pt-BR", "type": "voz"})  # ordem diferente
    c = ids.input_hash({"type": "voz", "locale": "en", "text": "hi"})
    check(a == b, "input_hash estável independe da ordem das chaves")
    check(a != c, "input_hash muda quando a entrada muda")


def test_redaction():
    print("test_redaction")
    tok = "1234567890:AAHtest-DUMMY-telegram-token-not-real-000000"
    out = ids.redact(f"conectando com token {tok} agora")
    check(tok not in out and "[REDACTED]" in out, "token de bot é redigido em log")
    out2 = ids.redact("OPENROUTER_API_KEY=sk-or-v1-abcdef1234567890abcdef")
    check("sk-or-v1" not in out2, "chave de API é redigida em log")


def test_quota_reserve():
    print("test_quota_reserve")
    tmp = os.path.join(tempfile.mkdtemp(), "t.db")
    conn = dbmod.connect(tmp)
    dbmod.migrate(conn)
    acc = ids.new_id("acc")
    conn.execute(
        "INSERT INTO provider_accounts(id,provider,quota_total,quota_remaining_observed,quota_reserved,status)"
        " VALUES (?,?,?,?,?,?)", (acc, "flow", 1000, 1000, 0, "ativo"))
    conn.commit()
    check(dbmod.reserve_quota(conn, acc, 800), "reserva 800 de 1000 ok")
    check(not dbmod.reserve_quota(conn, acc, 300), "reserva 300 além do saldo é negada")
    dbmod.consume_quota(conn, acc, reserved_amount=800, actual_amount=820)
    row = conn.execute("SELECT quota_remaining_observed, quota_reserved FROM provider_accounts WHERE id=?", (acc,)).fetchone()
    check(abs(row["quota_remaining_observed"] - 180) < 0.001, "consumo debita o real (1000-820=180)")
    check(abs(row["quota_reserved"]) < 0.001, "reserva liberada após consumo")
    conn.close()


def test_migrations():
    print("test_migrations")
    tmp = os.path.join(tempfile.mkdtemp(), "m.db")
    conn = dbmod.connect(tmp)
    applied = dbmod.migrate(conn)
    check(1 in applied, "migration 0001 aplicada")
    applied2 = dbmod.migrate(conn)
    check(applied2 == [], "migrate é idempotente (segunda vez não reaplica)")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for t in ["niches", "sources", "ideas", "language_variants", "jobs", "artifacts",
              "provider_accounts", "usage_events", "audit_events"]:
        check(t in tables, f"tabela {t} existe")
    conn.close()


def test_media_validation():
    print("test_media_validation")
    from app.domain import media
    good = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "45.0"},
    }
    r = media.evaluate_probe(good)
    check(r["ok"], "vídeo 1080x1920 h264 c/ áudio 45s aprovado")

    bad_ratio = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "45.0"},
    }
    r2 = media.evaluate_probe(bad_ratio)
    check(not r2["ok"] and not r2["checks"]["proporcao_9_16"], "vídeo 16:9 reprovado (proporção)")

    no_audio = {
        "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920}],
        "format": {"duration": "45.0"},
    }
    r3 = media.evaluate_probe(no_audio)
    check(not r3["ok"] and not r3["checks"]["tem_audio"], "vídeo sem áudio reprovado")

    too_long = dict(good); too_long["format"] = {"duration": "600"}
    r4 = media.evaluate_probe(too_long)
    check(not r4["ok"] and not r4["checks"]["duracao_ok"], "vídeo de 600s reprovado (duração)")


def test_repo_operations():
    print("test_repo_operations")
    from app.persistence import repo
    tmp = os.path.join(tempfile.mkdtemp(), "r.db")
    conn = dbmod.connect(tmp)
    dbmod.migrate(conn)

    nid = repo.niche_add(conn, "ferramentas digitais")
    iid = repo.idea_add(conn, "3 apps que economizam 1h/dia", niche_id=nid, objective="educacao")
    check(iid.startswith("idea_"), "idea_add cria ideia")

    # dedup de fontes
    s1, new1 = repo.source_add(conn, "https://Exemplo.com/Video ", platform="tiktok")
    s2, new2 = repo.source_add(conn, "https://exemplo.com/video", platform="tiktok")
    check(new1 and not new2 and s1 == s2, "source_add deduplica pela URL normalizada")

    # ciclo de estados válido
    repo.idea_transition(conn, iid, "pesquisando")
    repo.idea_transition(conn, iid, "analisando")
    repo.idea_transition(conn, iid, "selecionada")
    st = conn.execute("SELECT status FROM ideas WHERE id=?", (iid,)).fetchone()[0]
    check(st == "selecionada", "idea_transition segue o fluxo válido")

    # transição inválida barrada
    try:
        repo.idea_transition(conn, iid, "concluida")
        check(False, "transição inválida deveria levantar")
    except states.InvalidTransition:
        check(True, "idea_transition barra pulo inválido (selecionada->concluida)")

    # variantes: 3 locales, idempotente
    created = repo.variants_init(conn, iid)
    again = repo.variants_init(conn, iid)
    check(len(created) == 3 and len(again) == 0, "variants_init cria 3 locales e é idempotente")

    # jobs idempotentes
    j1, n1 = repo.job_start(conn, "voz", idea_id=iid, input_payload={"loc": "pt-BR"})
    j2, n2 = repo.job_start(conn, "voz", idea_id=iid, input_payload={"loc": "pt-BR"})
    check(n1 and not n2 and j1 == j2, "job_start é idempotente por input_hash")
    repo.job_finish(conn, j1, ok=True)
    fin = conn.execute("SELECT status FROM jobs WHERE id=?", (j1,)).fetchone()[0]
    check(fin == "concluido", "job_finish marca concluido")

    # auditoria registrada
    n_audit = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    check(n_audit >= 5, "audit_events registra as operações")
    conn.close()


def test_production_pipeline():
    print("test_production_pipeline")
    from app.media import subtitles, flow, delivery, pipeline
    from app.persistence import repo

    # --- legendas ---
    srt = subtitles.to_srt("Primeira frase. Segunda frase um pouco maior aqui. Terceira.", 30)
    v = subtitles.validate_srt(srt, 30)
    check(v["ok"] and v["cues"] >= 2, "SRT gerado é válido e tem múltiplos cues")
    bad = subtitles.validate_srt("1\n00:00:01,000 --> 00:09:00,000\nfora da duração\n", 30)
    check(not bad["ok"], "SRT com cue além da duração é reprovado")

    # --- flow manual vs api ---
    plan = flow.plan_scene({"index": 1, "prompt": "cena", "seconds": 8})
    check(plan["route"] == "manual" and plan["state"] == "aguardando_operacao_flow", "Flow em modo manual")
    import os as _os
    _os.environ["CONTENT_FLOW_MODE"] = "api"
    try:
        flow.plan_scene({"index": 1})
        check(False, "Flow api deveria ser bloqueado")
    except flow.FlowNotAuthorized:
        check(True, "Flow api bloqueado (sem autorização/gasto)")
    finally:
        _os.environ["CONTENT_FLOW_MODE"] = "manual"

    # --- setup banco + ideia + variante ---
    base = tempfile.mkdtemp()
    conn = dbmod.connect(os.path.join(base, "p.db"))
    dbmod.migrate(conn)
    iid = repo.idea_add(conn, "piloto")
    created = repo.variants_init(conn, iid)
    vid = dict(created)["pt-BR"]
    conn.execute("UPDATE language_variants SET script=? WHERE id=?",
                 ("Roteiro de teste. Segunda frase. Terceira frase final.", vid)); conn.commit()

    # --- caminho manual (backends padrão): legenda ok, voz+vídeo pendentes, não bloqueado ---
    rep = pipeline.produce_variant(conn, vid, target_seconds=30, artifacts_dir=os.path.join(base, "a1"))
    check("legenda:ok" in rep["steps"], "pipeline gera legenda mesmo em modo manual")
    check(any("Flow manual" in p for p in rep["pending"]) and not rep["blocked"],
          "vídeo fica pendente (Flow manual) e não bloqueia")
    st = conn.execute("SELECT status FROM language_variants WHERE id=?", (vid,)).fetchone()[0]
    check(st == "revisando", "variante aguarda em 'revisando' com pendências")

    # --- caminho feliz com stubs (arquivos reais) -> pronto ---
    class StubTTS:
        def synthesize(self, text, out):
            open(out, "wb").write(b"AUDIO"); return out
    class StubMontage:
        def assemble(self, plan, voice, srt_path, out):
            open(out, "wb").write(b"VIDEO"); return out
    vid2 = dict(repo.variants_init(conn, iid)) or {}
    # variants já existem; cria nova ideia para caminho limpo
    iid2 = repo.idea_add(conn, "piloto2")
    vid_ok = dict(repo.variants_init(conn, iid2))["en"]
    conn.execute("UPDATE language_variants SET script=? WHERE id=?", ("Frase um. Frase dois.", vid_ok)); conn.commit()
    rep2 = pipeline.produce_variant(conn, vid_ok, target_seconds=20,
                                    artifacts_dir=os.path.join(base, "a2"),
                                    tts_backend=StubTTS(), montage_backend=StubMontage())
    st2 = conn.execute("SELECT status FROM language_variants WHERE id=?", (vid_ok,)).fetchone()[0]
    check(st2 == "pronto", "caminho feliz com stubs leva a 'pronto'")
    nart = conn.execute("SELECT COUNT(*) FROM artifacts WHERE variant_id=?", (vid_ok,)).fetchone()[0]
    check(nart >= 3, "artefatos (voz/legenda/vídeo) registrados com hash")
    vok_row = dict(conn.execute("SELECT thumbnail_path, metadata_json FROM language_variants WHERE id=?", (vid_ok,)).fetchone())
    check(vok_row["thumbnail_path"] and os.path.isfile(vok_row["thumbnail_path"]), "capa (SVG 9:16) gerada e existe em disco")
    check(vok_row["metadata_json"] and "hashtags_base" in vok_row["metadata_json"], "metadados-base gravados (metadata_json)")
    ncov = conn.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type='cover' AND variant_id=?", (vid_ok,)).fetchone()[0]
    check(ncov == 1, "artefato de capa registrado com hash")

    # --- retomada após falha: backend falha 1x depois ok ---
    calls = {"n": 0}
    class FlakyTTS:
        def synthesize(self, text, out):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("tts caiu")
            open(out, "wb").write(b"AUDIO"); return out
    iid3 = repo.idea_add(conn, "piloto3")
    vid_f = dict(repo.variants_init(conn, iid3))["es"]
    conn.execute("UPDATE language_variants SET script=? WHERE id=?", ("Uno. Dos.", vid_f)); conn.commit()
    rep3 = pipeline.produce_variant(conn, vid_f, target_seconds=20,
                                    artifacts_dir=os.path.join(base, "a3"),
                                    tts_backend=FlakyTTS(), montage_backend=StubMontage())
    check("voz:ok" in rep3["steps"] and calls["n"] == 2, "retomada após falha: 2ª tentativa do TTS sucede")

    # --- entrega: MEDIA só para arquivos existentes ---
    vok = dict(conn.execute("SELECT * FROM language_variants WHERE id=?", (vid_ok,)).fetchone())
    pkg = delivery.variant_package(vok)
    check(any(l.startswith("MEDIA:") for l in pkg["media_lines"]), "entrega emite MEDIA: para arquivos reais")
    check("capa" not in pkg["missing"], "entrega inclui a capa gerada (não consta como faltando)")
    vpending = dict(conn.execute("SELECT * FROM language_variants WHERE id=?", (vid,)).fetchone())
    pkg2 = delivery.variant_package(vpending)
    check("vídeo final 9:16" in pkg2["missing"], "entrega marca vídeo pendente como faltando (sem MEDIA falso)")
    conn.close()


def test_pilot_runner():
    print("test_pilot_runner")
    from app import pilot
    base = tempfile.mkdtemp()
    conn = dbmod.connect(os.path.join(base, "pilot.db"))
    dbmod.migrate(conn)
    res = pilot.run_pilot(conn, artifacts_root=os.path.join(base, "art"), target_seconds=40)
    check(len(res["variants"]) == 6, "piloto produz 2 ideias x 3 idiomas = 6 variantes")
    nready = conn.execute("SELECT COUNT(*) FROM language_variants WHERE status='pronto'").fetchone()[0]
    check(nready == 0, "nenhuma variante marcada 'pronto' sem video real")
    nrev = conn.execute("SELECT COUNT(*) FROM language_variants WHERE status='revisando'").fetchone()[0]
    check(nrev == 6, "as 6 variantes aguardam em 'revisando' (video pendente)")
    ncap = conn.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type='caption'").fetchone()[0]
    check(ncap == 6, "6 legendas geradas (evidencia real)")
    nvid = conn.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type='video'").fetchone()[0]
    check(nvid == 0, "0 videos reais (Flow manual — nada fingido)")
    ncov = conn.execute("SELECT COUNT(*) FROM artifacts WHERE artifact_type='cover'").fetchone()[0]
    check(ncov == 6, "6 capas geradas (evidencia real)")
    nmeta = conn.execute("SELECT COUNT(*) FROM language_variants WHERE metadata_json IS NOT NULL").fetchone()[0]
    check(nmeta == 6, "metadados-base gravados nas 6 variantes")
    rep = pilot.phase_d_report(conn)
    check(rep["videos_reais"] == 0 and rep["variantes_prontas"] == 0, "relatorio Fase D nao finge 6 videos prontos")
    check(len(rep["dependencias_reais_restantes"]) == 2, "relatorio registra as 2 dependencias reais (LLM vivo + Flow manual)")
    conn.close()


def main() -> bool:
    for t in [test_state_transitions, test_idempotency, test_redaction, test_quota_reserve, test_migrations, test_media_validation, test_repo_operations, test_production_pipeline, test_pilot_runner]:
        t()
    print()
    if _failures:
        print(f"RESULTADO: {len(_failures)} FALHA(S)")
        return False
    print("RESULTADO: TODOS OS TESTES PASSARAM")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

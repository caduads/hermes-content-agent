"""Orquestrador do pipeline de produção de UMA variante de idioma.

Fluxo: adaptando -> produzindo_voz -> montando -> revisando -> pronto
(estado por variante, validado). Idempotência e retomada por jobs.

Backends injetáveis (para testar sem ferramentas externas e não declarar vídeo real sem evidência):
- tts_backend.synthesize(text, out_path) -> caminho do áudio ou None (None = pendente/manual)
- montage_backend.assemble(scene_plan, voice_path, srt_path, out_path) -> caminho do vídeo ou None
No container, o backend de voz é o TTS nativo do Hermes (Edge TTS grátis) e a montagem usa ffmpeg;
o vídeo das cenas vem do Flow em modo manual (out=None até o operador informar o arquivo).
"""
from __future__ import annotations

import os

from app.persistence import repo
from app.domain import ids
from app.media import subtitles, review as review_mod


class ManualTTS:
    """Sem geração automática: sinaliza pendência (o agente/Hermes fará via TTS nativo)."""
    def synthesize(self, text, out_path):
        return None


class ManualMontage:
    """Flow manual: não monta automaticamente; vídeo fica pendente até arquivo informado."""
    def assemble(self, scene_plan, voice_path, srt_path, out_path):
        return None


def _retry(fn, max_attempts):
    """Executa fn() com retomada; retorna (result, attempts, last_error)."""
    last = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(), attempt, None
        except Exception as e:  # falha de backend
            last = str(e)
    return None, max_attempts, last


def produce_variant(conn, variant_id, target_seconds=45, artifacts_dir=None,
                    tts_backend=None, montage_backend=None, max_attempts=3):
    """Produz uma variante ponta a ponta (determinístico + retomada). Retorna um relatório."""
    tts = tts_backend or ManualTTS()
    montage = montage_backend or ManualMontage()
    row = conn.execute(
        "SELECT id, idea_id, locale, script, status, revision_count FROM language_variants WHERE id=?",
        (variant_id,)).fetchone()
    if row is None:
        raise ValueError(f"variante {variant_id} não existe")
    locale = row["locale"]
    script = row["script"] or f"[roteiro pendente para {locale}]"
    artifacts_dir = artifacts_dir or os.path.join(os.getcwd(), "data", "artifacts", variant_id)
    os.makedirs(artifacts_dir, exist_ok=True)
    report = {"variant_id": variant_id, "locale": locale, "steps": [], "pending": [], "blocked": False}

    def step(name):
        report["steps"].append(name)

    # 1) adaptando (script já preparado pela skill localization)
    if row["status"] == "aguardando":
        repo.variant_transition(conn, variant_id, "adaptando")

    # 2) produzindo_voz
    if conn.execute("SELECT status FROM language_variants WHERE id=?", (variant_id,)).fetchone()[0] == "adaptando":
        repo.variant_transition(conn, variant_id, "produzindo_voz")
    jid, _ = repo.job_start(conn, "voz", variant_id=variant_id, input_payload={"loc": locale})
    voice_out = os.path.join(artifacts_dir, f"voice_{locale}.mp3")
    voice, attempts, err = _retry(lambda: tts.synthesize(script, voice_out), max_attempts)
    if err:
        repo.job_finish(conn, jid, ok=False, error_code="tts", error_message=err)
        step("voz:falha")
    else:
        repo.job_finish(conn, jid, ok=True)
        if voice and os.path.isfile(voice):
            _record_artifact(conn, variant_id, row["idea_id"], "voice", voice)
            conn.execute("UPDATE language_variants SET voice_path=? WHERE id=?", (voice, variant_id)); conn.commit()
            step("voz:ok")
        else:
            report["pending"].append("narração (TTS nativo do Hermes / manual)")
            step("voz:pendente")

    # 3) legendas (determinístico, sempre gerável a partir do roteiro)
    srt_path = os.path.join(artifacts_dir, f"legenda_{locale}.srt")
    srt_text = subtitles.to_srt(script, target_seconds)
    with open(srt_path, "w", encoding="utf-8") as fh:
        fh.write(srt_text)
    _record_artifact(conn, variant_id, row["idea_id"], "caption", srt_path)
    conn.execute("UPDATE language_variants SET caption_path=? WHERE id=?", (srt_path, variant_id)); conn.commit()
    step("legenda:ok")

    # 4) montando (Flow: manual por padrão -> vídeo pendente)
    if conn.execute("SELECT status FROM language_variants WHERE id=?", (variant_id,)).fetchone()[0] == "produzindo_voz":
        repo.variant_transition(conn, variant_id, "montando")
    jid2, _ = repo.job_start(conn, "video", variant_id=variant_id, input_payload={"loc": locale})
    video_out = os.path.join(artifacts_dir, f"video_{locale}.mp4")
    scene_plan = []
    video, attempts2, err2 = _retry(
        lambda: montage.assemble(scene_plan, voice, srt_path, video_out), max_attempts)
    if err2:
        repo.job_finish(conn, jid2, ok=False, error_code="montage", error_message=err2)
        step("video:falha")
    else:
        repo.job_finish(conn, jid2, ok=True)
        if video and os.path.isfile(video):
            _record_artifact(conn, variant_id, row["idea_id"], "video", video)
            conn.execute("UPDATE language_variants SET video_path=? WHERE id=?", (video, variant_id)); conn.commit()
            step("video:ok")
        else:
            report["pending"].append("vídeo (Flow manual — aguardando_operacao_flow)")
            step("video:pendente")

    # 5) revisando
    if conn.execute("SELECT status FROM language_variants WHERE id=?", (variant_id,)).fetchone()[0] == "montando":
        repo.variant_transition(conn, variant_id, "revisando")
    vrow = dict(conn.execute("SELECT * FROM language_variants WHERE id=?", (variant_id,)).fetchone())
    rev = review_mod.review_variant(vrow, srt_text=srt_text, video_probe=None, max_seconds=target_seconds + 50)
    report["review"] = rev

    # 6) desfecho
    if rev["ok"] and not report["pending"]:
        repo.variant_transition(conn, variant_id, "pronto")
        step("pronto")
    elif report["pending"]:
        # não reprovado: aguardando etapa manual (Flow/voz). Mantém em revisando.
        step("aguardando_pendencias")
    else:
        # reprovado: aplica limite de revisão
        rc = vrow["revision_count"] or 0
        if review_mod.revision_allowed(rc):
            conn.execute("UPDATE language_variants SET revision_count=? WHERE id=?", (rc + 1, variant_id)); conn.commit()
            step(f"revisao:{rc + 1}")
        else:
            repo.variant_transition(conn, variant_id, "bloqueado")
            report["blocked"] = True
            step("bloqueado")
    return report


def _record_artifact(conn, variant_id, idea_id, atype, path):
    sha = ids.sha256_file(path) if os.path.isfile(path) else None
    size = os.path.getsize(path) if os.path.isfile(path) else None
    conn.execute(
        "INSERT INTO artifacts(id,idea_id,variant_id,artifact_type,path,sha256,size_bytes) VALUES (?,?,?,?,?,?,?)",
        (ids.new_id("art"), idea_id, variant_id, atype, path, sha, size))
    conn.commit()

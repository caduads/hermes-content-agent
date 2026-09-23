---
name: production
description: Produtor. Converte o roteiro em plano de cenas, organiza visuais, produz narração (TTS), sincroniza legendas, monta e exporta o vídeo 9:16. Use quando a variante entra em 'produzindo_voz'/'montando'.
---

# Produção (voz, cenas, legendas, montagem)

Transforma o roteiro adaptado em vídeo final vertical (9:16). Grava artefatos em `artifacts` (com sha256)
e caminhos na `language_variants` (`voice_path`, `caption_path`, `video_path`, `thumbnail_path`).

## Ordem
1. Plano de cenas a partir do `scene_plan_json`.
2. Visuais: **priorizar cenas SEM texto embutido e sem movimento labial dependente de idioma** — assim o
   mesmo material visual é reutilizável entre pt-BR/en/es (economiza créditos).
3. Narração: TTS (default dev = Edge TTS grátis; precisa ffmpeg). Um `voice_path` por idioma.
4. Legendas: gerar SRT/VTT sincronizado.
5. Montagem/export: 9:16, master limpo + exportações por plataforma.

## Comandos reais
Rode a partir de `cd /app/content-agent`.
- Produzir uma variante (voz→legenda→montagem→revisão, com retomada e limite de 2 revisões):
  `python contentctl.py produce --variant <id> --seconds 45`
  Em modo padrão a voz usa o TTS nativo do Hermes e o vídeo fica `aguardando_operacao_flow` (manual).
  O relatório traz `pending` (o que falta) e `blocked` (se estourou as 2 revisões).
- Ver a ordem de trabalho manual do Flow: `python contentctl.py flow-order`.
- Montar a entrega de uma ideia (tags MEDIA só dos arquivos que existem): `python contentctl.py deliver --idea <id>`.
  Emita as linhas `MEDIA:<caminho>` na resposta para o Hermes anexar os arquivos no Telegram.

## Google Flow (regra crítica)
Não presumir consumo dos créditos do produto Flow via API Veo (faturamentos distintos). Enquanto não houver
via oficialmente permitida validada, o job de vídeo entra no estado **`aguardando_operacao_flow`** com
instruções claras para uma etapa manual — todo o resto permanece automatizado. Reservar cota antes de gerar
(`reserve_quota`), registrar custo exibido antes e débito observado depois (`usage_events`). Cobrança por
GERAÇÃO, não por prompt; confirmar histórico antes de repetir tentativa incerta (idempotência por `input_hash`).

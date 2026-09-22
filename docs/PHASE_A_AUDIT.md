# Fase A — Auditoria do Hermes Agent (ambiente-alvo: Railway)

Data: 2026-09-22 • Alvo: serviço `hermes-railway-template` (Railway), imagem `nousresearch/hermes-agent:latest`.

## Como este deploy funciona (mecânica de injeção de customização)

- Imagem oficial `nousresearch/hermes-agent`, com `HERMES_HOME=/data/.hermes` e `HOME=/data`.
- `scripts/entrypoint.sh` (no repo do template) roda no boot: grava as variáveis de ambiente em
  `/data/.hermes/.env`, cria `/data/.hermes/config.yaml` se não existir, e executa `hermes gateway`.
- **Todo o estado e customização vivem no volume persistente `/data/.hermes/`**: `config.yaml`, `.env`,
  `logs/`, `sessions/`, `cron/`, `pairing/`, e (quando existirem) `skills/`.
- O template NÃO embute skills na imagem. Para versionar skills/config e reimplantá-las, o caminho
  correto é: **fork do template** + estender o `entrypoint.sh` para SINCRONIZAR uma pasta `skills/` e
  um `config.yaml` do repo para `/data/.hermes/` no boot. Assim: commit no repo -> redeploy -> skills atualizadas.

## O que é NATIVO (reaproveitar — NÃO reconstruir)

| Necessidade do briefing | Recurso nativo do Hermes |
|---|---|
| Interface Telegram, allowlist | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` (deny-all por padrão) |
| Tópicos (Central, Nichos, Produção, Entregas, Custos) | **DM Topics** (`platforms.telegram.extra.dm_topics`) com `skill:` por tópico + `/topic` |
| Comandos (/status, /pesquisar_nichos, ...) | Registro de slash-commands + menu (`/setcommands`) + inline picker |
| Entrega de arquivos (vídeo, SRT, capa, zip) | Tag `MEDIA:/caminho` (mp4, srt/vtt via txt, png, zip, pdf... nativos) |
| Arquivos > 20MB | Local Bot API server (limite 2GB) — etapa opcional de infra |
| Agendamentos (pesquisa semanal, resumo diário, backup) | **Cron nativo** (`/data/.hermes/cron`) |
| Voz (narração) | TTS nativo: **Edge TTS grátis** (precisa ffmpeg p/ voz-bubble) / OpenAI / ElevenLabs |
| Transcrição | STT nativo: `faster-whisper` local (sem chave) / Groq / OpenAI |
| Roteamento multi-provedor de LLM | Env nativas: `OPENROUTER_API_KEY`, `OPENAI_BASE_URL+KEY`, `ANTHROPIC`, `GOOGLE/GEMINI`, `XAI`, `DEEPSEEK`, `DASHSCOPE` (Qwen), `KIMI`, `GLM`, `HF_TOKEN`, `MINIMAX`, `COPILOT` + `LLM_MODEL`, `HERMES_INFERENCE_PROVIDER` |
| Perguntas interativas (confirmar antes de gastar) | Ferramenta `clarify` (botões inline no Telegram) |
| Aprovação de comando perigoso | Exec Approval nativo (pede "yes/no" no chat) |
| Persistência de sessões | SQLite nativo em `/data/.hermes/state.db` (+ nosso DB de domínio) |
| Skills como especialistas | Hermes Skills (markdown) + binding por tópico |

## O que o PROJETO precisa CONSTRUIR (extensão mínima)

1. **Banco de domínio** (SQLite em `/data`): tabelas de niches, sources, ideas, language_variants,
   jobs, artifacts, provider_accounts, usage_events, audit_events (seção 14 do briefing). O `state.db`
   nativo é do Hermes; o nosso é separado (`/data/content-agent/db/content.db`).
2. **Skills especialistas** (coordenador, pesquisa, análise, roteiro, localização, produção, revisão)
   como Hermes Skills que operam sobre o nosso banco.
3. **Máquina de estados** das ideias e das variantes de idioma (idempotência por `input_hash`).
4. **Camada de controle de custos/cotas** (reserva/consumo transacional) — sobre `provider_accounts`/`usage_events`.
5. **Adaptador Google Flow** (ver risco abaixo) — provavelmente estado `aguardando_operacao_flow` (manual).
6. **Validação de mídia** (ffprobe/ffmpeg): proporção 9:16, codec, duração, áudio, legendas.
7. **Sincronização repo -> /data** no `entrypoint.sh` (fork) para deploy versionado das skills/config.

## Riscos confirmados na auditoria

- **Google Flow:** créditos são do produto web; NÃO há prova de consumo via API Veo (faturamento à parte).
  Automatizar a UI fere termos. Tratar como etapa manual (`aguardando_operacao_flow`) até prova oficial.
- **LLMs grátis instáveis:** camada de fallback é obrigatória. Modelos grátis disponíveis hoje no OpenRouter
  incluem `nvidia/nemotron-3.5-lightning:free` (ctx 1M) e `qwen/qwen3.8-27b:free`.
- **ffmpeg** é necessário para narração em voz-bubble (Edge TTS). Verificar presença na imagem.
- **Deploy versionado** exige o fork do template (o serviço atual aponta para `lovexbytes/` upstream,
  que não é editável pelo operador).

## Pendências de operador que este projeto respeita com defaults seguros

Ver seção 26 do briefing. Nenhuma bloqueia a base técnica; marcadas como `pendente` no `config/project.yaml`.

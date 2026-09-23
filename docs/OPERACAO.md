# Manual de Operação — content-agent

Operação autônoma de conteúdo sobre o **Hermes Agent**, controlada pelo **Telegram**.
Deploy atual: Railway (imagem oficial `nousresearch/hermes-agent` + nossos ativos, via `Dockerfile`
que copia `app/skills/config/migrations/contentctl.py` e `entrypoint.sh` que sincroniza no boot).

## 1. Instalação do zero (resumo)
1. Repo público: `caduads/hermes-content-agent` (Railway aponta para ele, branch `main`).
2. Variáveis no serviço (Railway → Variables): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS=8974266170`,
   `OPENROUTER_API_KEY`, `LLM_MODEL=nvidia/nemotron-3.5-lightning:free` (grátis). Sem add-ons pagos.
3. Deploy: no boot o `entrypoint.sh` sincroniza skills/config para `/data/.hermes`, cria o banco de
   domínio (`/data/content-agent/db/content.db`, 11 tabelas) e registra os cron jobs.
4. Verificar: logs devem mostrar `[content-agent] Sincronizacao concluida.` e `[Telegram] Connected`.

## 2. Comandos (rodar em `cd /app/content-agent`)
- `python contentctl.py status` — resumo operacional.
- `python contentctl.py healthcheck` — saúde do banco/schema (sai 0/1).
- `python contentctl.py list --entity ideas|niches|sources|variants|jobs`.
- `python contentctl.py niche-add|niche-score|source-add|idea-add|idea-transition|variants-init|variant-transition|job-start|job-finish|usage-add`.
- `python contentctl.py produce --variant <id> [--seconds 45]` — voz→legenda→montagem→revisão (retomável).
- `python contentctl.py deliver --idea <id>` — manifesto de entrega (tags `MEDIA:` só de arquivos reais).
- `python contentctl.py flow-order` — ordem de trabalho manual do Flow.
- `python contentctl.py pilot` — roda o piloto (2 ideias × 3 idiomas).
- `python contentctl.py report` — relatório da Fase D (autonomia/custo/pendências).

## 3. Comandos do Telegram (via skills)
`/status /pesquisar_nichos /listar_ideias /produzir <id> /pausar /retomar /custos /falhas /cancelar <id> /ajuda`
(a skill `review` é `/skill review` — colide com um comando nativo). Também linguagem natural.

## 4. Pausar / Retomar
- Fila/cron: `hermes pause` (parada global) / `hermes resume`. Um job: `hermes cron pause|resume <nome>`.
- Pausar não corrompe geração em andamento: a montagem/Flow é manual; jobs são idempotentes.

## 5. Atualizar (novo código)
1. Commit em `main` (via branch + fast-forward por API — push direto em `main` é bloqueado por política).
2. Reapontar/redeployar o serviço (Railway rebuild do `Dockerfile`).
3. O `entrypoint` re-sincroniza skills/config e aplica migrations novas automaticamente.

## 6. Backup / Restore / Healthcheck
- **Backup**: cron `content-daily-backup` (no-agent) copia `content.db` para `/data/content-agent/backups/`
  (mantém as 15 mais recentes). Manual: `hermes cron run content-daily-backup`.
- **Restore**: pare o gateway, copie `backups/content-<ts>.db` sobre `/data/content-agent/db/content.db`,
  reinicie. Migrations são idempotentes.
- **Healthcheck**: `python contentctl.py healthcheck` (banco/schema). Fila/cron: `hermes cron doctor`,
  `hermes cron status`.

## 7. Recuperação de falhas
- Jobs são idempotentes por `input_hash` — repetir não duplica trabalho nem gasto.
- Variante que falha é retomável (estados `falha`→retomar); revisão tem **limite de 2 rodadas**,
  depois marca `bloqueado` e reporta no Telegram (nunca loop infinito).
- Estados/artefatos sobrevivem a reinício (persistidos no volume `/data`).

## 8. Arquitetura (resumo)
```
Telegram ─▶ Gateway Hermes ─▶ Coordenador (skill) ─▶ [research | opportunity-analysis | scripting
   | localization | production | review] ─▶ contentctl/app ─▶ SQLite (/data/content-agent/db)
                                                          └─▶ artifacts (/data/content-agent/artifacts)
Cron: pesquisa semanal · oportunidades (dias úteis) · digest diário · fila 6/6h · backup diário
Vídeo: Google Flow em modo MANUAL (aguardando_operacao_flow) — sem API paga, sem automação web.
```

## 9. Dependências reais restantes (fora do software)
Ver `PENDING_OPERATOR.md` — (1) execução viva do LLM para pesquisa/roteiro/localização; (2) operação
manual do Flow para o vídeo real. Nenhuma bloqueia o desenvolvimento; ambas são de operação/decisão.

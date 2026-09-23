#!/usr/bin/env bash
set -euo pipefail

export HERMES_HOME="${HERMES_HOME:-/data/.hermes}"
export HOME=/data
LEGACY_MESSAGING_CWD="${MESSAGING_CWD:-/data/workspace}"

INIT_MARKER="${HERMES_HOME}/.initialized"
ENV_FILE="${HERMES_HOME}/.env"
CONFIG_FILE="${HERMES_HOME}/config.yaml"
DEFAULT_TERMINAL_CWD="${TERMINAL_CWD:-${LEGACY_MESSAGING_CWD}}"

mkdir -p "${HERMES_HOME}" "${HERMES_HOME}/logs" "${HERMES_HOME}/sessions" "${HERMES_HOME}/cron" "${HERMES_HOME}/pairing" "${DEFAULT_TERMINAL_CWD}"

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

validate_platforms() {
  local count=0

  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    count=$((count + 1))
  fi

  if [[ -n "${DISCORD_BOT_TOKEN:-}" ]]; then
    count=$((count + 1))
  fi

  if [[ -n "${SLACK_BOT_TOKEN:-}" || -n "${SLACK_APP_TOKEN:-}" ]]; then
    if [[ -z "${SLACK_BOT_TOKEN:-}" || -z "${SLACK_APP_TOKEN:-}" ]]; then
      echo "[bootstrap] ERROR: Slack requires both SLACK_BOT_TOKEN and SLACK_APP_TOKEN." >&2
      exit 1
    fi
    count=$((count + 1))
  fi

  if [[ "$count" -lt 1 ]]; then
    echo "[bootstrap] ERROR: Configure at least one platform: Telegram, Discord, or Slack." >&2
    exit 1
  fi
}

has_valid_provider_config() {
  if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${OPENAI_BASE_URL:-}" && -n "${OPENAI_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" || -n "${ANTHROPIC_TOKEN:-}" ]]; then return 0; fi
  if [[ -n "${GOOGLE_API_KEY:-}" || -n "${GEMINI_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${XAI_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${DASHSCOPE_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${KIMI_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${GLM_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${HF_TOKEN:-}" ]]; then return 0; fi
  if [[ -n "${AI_GATEWAY_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${MINIMAX_API_KEY:-}" ]]; then return 0; fi
  if [[ -n "${COPILOT_GITHUB_TOKEN:-}" ]]; then return 0; fi

  return 1
}

append_if_set() {
  local key="$1"
  local val="${!key:-}"
  if [[ -n "$val" ]]; then
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

read_env_value() {
  local file="$1"
  local key="$2"

  if [[ ! -f "$file" ]]; then
    return 1
  fi

  grep -E "^${key}=" "$file" | head -n 1 | cut -d '=' -f 2-
}

config_has_terminal_cwd() {
  if [[ ! -f "$CONFIG_FILE" ]]; then
    return 1
  fi

  awk '
    /^terminal:[[:space:]]*$/ { in_terminal = 1; next }
    in_terminal && /^[^[:space:]]/ { in_terminal = 0 }
    in_terminal && /^[[:space:]]+cwd:[[:space:]]*/ { found = 1; exit }
    END { exit(found ? 0 : 1) }
  ' "$CONFIG_FILE"
}

config_has_terminal_section() {
  [[ -f "$CONFIG_FILE" ]] && grep -qE '^terminal:[[:space:]]*$' "$CONFIG_FILE"
}

create_default_config() {
  echo "[bootstrap] Creating ${CONFIG_FILE}"
  cat > "$CONFIG_FILE" <<EOF
terminal:
  backend: ${TERMINAL_ENV:-${TERMINAL_BACKEND:-local}}
  cwd: $1
  timeout: ${TERMINAL_TIMEOUT:-180}
compression:
  enabled: true
  threshold: 0.85
EOF
}

ensure_terminal_cwd_in_config() {
  local cwd="$1"
  local tmp_file

  if [[ ! -f "$CONFIG_FILE" ]]; then
    create_default_config "$cwd"
    return 0
  fi

  if config_has_terminal_cwd; then
    return 0
  fi

  if config_has_terminal_section; then
    tmp_file="$(mktemp)"
    awk -v cwd="$cwd" '
      /^terminal:[[:space:]]*$/ && !inserted {
        print
        print "  cwd: " cwd
        inserted = 1
        next
      }
      { print }
    ' "$CONFIG_FILE" > "$tmp_file"
    mv "$tmp_file" "$CONFIG_FILE"
    return 0
  fi

  printf '\nterminal:\n  cwd: %s\n' "$cwd" >> "$CONFIG_FILE"
}

migrate_legacy_messaging_cwd() {
  local persisted_cwd legacy_cwd

  persisted_cwd="$(read_env_value "$ENV_FILE" "MESSAGING_CWD" || true)"
  legacy_cwd="${persisted_cwd:-${MESSAGING_CWD:-}}"

  if [[ -n "$legacy_cwd" ]]; then
    ensure_terminal_cwd_in_config "$legacy_cwd"
  elif [[ ! -f "$CONFIG_FILE" ]]; then
    create_default_config "$DEFAULT_TERMINAL_CWD"
  fi
}

configure_agent_cache_memory_limit() {
  local value="${AGENT_CACHE_MEMORY_HIGH_MB:-}"

  if [[ -z "$value" ]]; then
    return 0
  fi

  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "[bootstrap] ERROR: AGENT_CACHE_MEMORY_HIGH_MB must be a positive integer in MB." >&2
    exit 1
  fi

  echo "[bootstrap] Setting Hermes agent-cache anonymous-RSS budget to ${value} MB."
  hermes config set agent.agent_cache.memory_high_mb "$value"
}

if ! has_valid_provider_config; then
  echo "[bootstrap] ERROR: Configure a provider: OPENROUTER_API_KEY, or OPENAI_BASE_URL+OPENAI_API_KEY, or ANTHROPIC_API_KEY." >&2
  exit 1
fi

validate_platforms

migrate_legacy_messaging_cwd
configure_agent_cache_memory_limit

echo "[bootstrap] Writing runtime env to ${ENV_FILE}"
{
  echo "# Managed by entrypoint.sh"
  echo "HERMES_HOME=${HERMES_HOME}"
} > "$ENV_FILE"

for key in \
  OPENROUTER_API_KEY OPENAI_API_KEY OPENAI_BASE_URL ANTHROPIC_API_KEY ANTHROPIC_TOKEN GOOGLE_API_KEY GEMINI_API_KEY XAI_API_KEY DEEPSEEK_API_KEY DASHSCOPE_API_KEY KIMI_API_KEY GLM_API_KEY HF_TOKEN AI_GATEWAY_API_KEY MINIMAX_API_KEY COPILOT_GITHUB_TOKEN LLM_MODEL HERMES_INFERENCE_PROVIDER HERMES_PORTAL_BASE_URL NOUS_INFERENCE_BASE_URL HERMES_NOUS_MIN_KEY_TTL_SECONDS HERMES_DUMP_REQUESTS \
  TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_USERS TELEGRAM_ALLOW_ALL_USERS TELEGRAM_HOME_CHANNEL TELEGRAM_HOME_CHANNEL_NAME TELEGRAM_PROXY \
  DISCORD_BOT_TOKEN DISCORD_ALLOWED_USERS DISCORD_ALLOW_ALL_USERS DISCORD_HOME_CHANNEL DISCORD_HOME_CHANNEL_NAME DISCORD_REQUIRE_MENTION DISCORD_FREE_RESPONSE_CHANNELS DISCORD_REPLY_TO_MODE \
  SLACK_BOT_TOKEN SLACK_APP_TOKEN SLACK_ALLOWED_USERS SLACK_ALLOW_ALL_USERS SLACK_HOME_CHANNEL SLACK_HOME_CHANNEL_NAME WHATSAPP_ENABLED WHATSAPP_ALLOWED_USERS \
  GATEWAY_ALLOW_ALL_USERS API_SERVER_ENABLED API_SERVER_KEY API_SERVER_PORT API_SERVER_HOST API_SERVER_MODEL_NAME \
  FIRECRAWL_API_KEY NOUS_API_KEY BROWSERBASE_API_KEY BROWSERBASE_PROJECT_ID BROWSERBASE_PROXIES BROWSERBASE_ADVANCED_STEALTH BROWSER_SESSION_TIMEOUT BROWSER_INACTIVITY_TIMEOUT FAL_KEY ELEVENLABS_API_KEY VOICE_TOOLS_OPENAI_KEY \
  TINKER_API_KEY WANDB_API_KEY RL_API_URL GITHUB_TOKEN \
  TERMINAL_ENV TERMINAL_BACKEND TERMINAL_DOCKER_IMAGE TERMINAL_SINGULARITY_IMAGE TERMINAL_MODAL_IMAGE TERMINAL_CWD TERMINAL_TIMEOUT TERMINAL_LIFETIME_SECONDS TERMINAL_CONTAINER_CPU TERMINAL_CONTAINER_MEMORY TERMINAL_CONTAINER_DISK TERMINAL_CONTAINER_PERSISTENT TERMINAL_SANDBOX_DIR TERMINAL_SSH_HOST TERMINAL_SSH_USER TERMINAL_SSH_PORT TERMINAL_SSH_KEY SUDO_PASSWORD \
  WEB_TOOLS_DEBUG VISION_TOOLS_DEBUG MOA_TOOLS_DEBUG IMAGE_TOOLS_DEBUG CONTEXT_COMPRESSION_ENABLED CONTEXT_COMPRESSION_THRESHOLD CONTEXT_COMPRESSION_MODEL HERMES_MAX_ITERATIONS HERMES_TOOL_PROGRESS HERMES_TOOL_PROGRESS_MODE
do
  append_if_set "$key"
done

if [[ ! -f "$INIT_MARKER" ]]; then
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$INIT_MARKER"
  echo "[bootstrap] First-time initialization completed."
else
  echo "[bootstrap] Existing Hermes data found. Skipping one-time init."
fi

if [[ -z "${TELEGRAM_ALLOWED_USERS:-}${DISCORD_ALLOWED_USERS:-}${SLACK_ALLOWED_USERS:-}" ]]; then
  if ! is_true "${GATEWAY_ALLOW_ALL_USERS:-}" && ! is_true "${TELEGRAM_ALLOW_ALL_USERS:-}" && ! is_true "${DISCORD_ALLOW_ALL_USERS:-}" && ! is_true "${SLACK_ALLOW_ALL_USERS:-}"; then
    echo "[bootstrap] WARNING: No allowlists configured. Gateway defaults to deny-all; use DM pairing or set *_ALLOWED_USERS." >&2
  fi
fi

# --- content-agent: sincroniza skills/config e prepara o banco de dominio ---
CONTENT_SRC="/app/content-agent"
if [[ -d "${CONTENT_SRC}" ]]; then
  echo "[content-agent] Sincronizando skills e config para ${HERMES_HOME}..."
  mkdir -p "${HERMES_HOME}/skills" "/data/content-agent/db" "/data/content-agent/artifacts"
  cp -r "${CONTENT_SRC}/skills/." "${HERMES_HOME}/skills/" 2>/dev/null || true
  cp -f "${CONTENT_SRC}/config/project.yaml" "/data/content-agent/project.yaml" 2>/dev/null || true
  export CONTENT_DB_PATH="${CONTENT_DB_PATH:-/data/content-agent/db/content.db}"
  if command -v python >/dev/null 2>&1; then
    ( cd "${CONTENT_SRC}" && python contentctl.py db-init --db "${CONTENT_DB_PATH}" ) \
      || echo "[content-agent] aviso: db-init falhou (segue mesmo assim)"
  fi
  echo "[content-agent] Sincronizacao concluida."
fi

# --- content-agent: registrar cron jobs (idempotente por marcador versionado) ---
CRON_MARKER="${HERMES_HOME}/.content-agent-cron-seeded-v1"
if [[ -d "/app/content-agent" && ! -f "${CRON_MARKER}" ]]; then
  echo "[content-agent] Registrando cron jobs..."
  CA_DELIVER="${CONTENT_CRON_DELIVER:-telegram:8974266170}"
  hermes cron create "every sunday 9am" \
    "Voce e o content-agent. Rode a skill research: compare ate 3 nichos candidatos com >=10 fontes de >=5 criadores quando as fontes permitirem. Grave cada fonte com 'cd /app/content-agent && python contentctl.py source-add ...' e cada nicho com niche-add. Entregue ranking com evidencias e limitacoes. Nunca invente metricas; sem dado use desconhecido." \
    --skill research --name content-weekly-research --deliver "$CA_DELIVER" \
    || echo "[content-agent] aviso: cron weekly-research nao criado"
  hermes cron create "weekdays at 8am" \
    "Voce e o content-agent. Atualizacao curta: cheque sinais novos nos nichos ja registrados (cd /app/content-agent && python contentctl.py list --entity niches) e registre fontes novas relevantes. Se nada relevante mudou, responda apenas [SILENT]." \
    --skill research --continuity --name content-weekday-opportunities --deliver "$CA_DELIVER" \
    || echo "[content-agent] aviso: cron weekday-opportunities nao criado"
  hermes cron create "daily at 7am" \
    "Voce e o coordenador do content-agent. Rode 'cd /app/content-agent && python contentctl.py status' e entregue um resumo do que mudou (ideias por estado, custos, proxima acao, falhas). Se nada mudou, responda apenas [SILENT]." \
    --skill coordinator --continuity --name content-daily-digest --deliver "$CA_DELIVER" \
    || echo "[content-agent] aviso: cron daily-digest nao criado"
  hermes cron create "every 6h" \
    "Coordenador do content-agent: verifique jobs travados e itens em falha (cd /app/content-agent && python contentctl.py list --entity jobs; python contentctl.py status). Se houver bloqueio real, reporte; senao responda apenas [SILENT]." \
    --skill coordinator --name content-queue-check --deliver "$CA_DELIVER" \
    || echo "[content-agent] aviso: cron queue-check nao criado"
  # backup diario (no-agent): script em $HERMES_HOME/scripts
  mkdir -p "${HERMES_HOME}/scripts"
  cat > "${HERMES_HOME}/scripts/content-backup.sh" <<'BK'
#!/bin/bash
set -e
DB="${CONTENT_DB_PATH:-/data/content-agent/db/content.db}"
BKDIR="/data/content-agent/backups"
mkdir -p "$BKDIR"
if [ -f "$DB" ]; then
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  cp "$DB" "$BKDIR/content-$ts.db"
  ls -1t "$BKDIR"/content-*.db 2>/dev/null | tail -n +15 | xargs -r rm -f
  echo "[content-agent] backup ok: content-$ts.db"
else
  echo "[content-agent] backup: banco ainda nao existe"
fi
BK
  chmod +x "${HERMES_HOME}/scripts/content-backup.sh"
  hermes cron create "daily at 3am" --no-agent --script content-backup.sh \
    --name content-daily-backup --deliver "$CA_DELIVER" \
    || echo "[content-agent] aviso: cron daily-backup nao criado"
  touch "${CRON_MARKER}"
  echo "[content-agent] Cron jobs registrados (marcador v1)."
fi

# --- content-agent: pin OPCIONAL de modelo nos crons (defesa contra drift_skip) ---
# O drift_skip do Hermes PULA crons NAO fixados quando o modelo global muda (sem gasto, silencioso).
# Os crons content-* sao criados sem pin. Para blinda-los, defina AMBAS as variaveis no Railway:
#   CONTENT_CRON_PROVIDER  (ex.: openrouter)
#   CONTENT_CRON_MODEL     (ex.: nvidia/nemotron-3.5-lightning:free  -- modelo GRATIS validado)
# Sem elas, o comportamento nao muda. Roda a cada boot (idempotente).
if [[ -n "${CONTENT_CRON_PROVIDER:-}" && -n "${CONTENT_CRON_MODEL:-}" ]]; then
  echo "[content-agent] Fixando modelo dos crons (${CONTENT_CRON_PROVIDER}/${CONTENT_CRON_MODEL})..."
  for j in content-weekly-research content-weekday-opportunities content-daily-digest content-queue-check; do
    hermes cron edit "$j" --provider "${CONTENT_CRON_PROVIDER}" --model "${CONTENT_CRON_MODEL}" \
      || echo "[content-agent] aviso: pin do cron ${j} nao aplicado"
  done
fi

echo "[bootstrap] Starting Hermes gateway..."
unset MESSAGING_CWD
exec hermes gateway

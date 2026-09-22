# AGENTS.md — content-agent

Operação autônoma de conteúdo coordenada pelo **Hermes Agent** e controlada pelo **Telegram**.
Roda na nuvem (Railway agora; Hostinger depois). Pesquisa nichos, produz conteúdo em pt-BR/en/es,
revisa e entrega pelo Telegram. **Não publica** em redes sociais (fora do escopo do MVP).

## Regra de ouro
Reaproveitar o que o Hermes já faz (ver `docs/PHASE_A_AUDIT.md`). Só construímos a "extensão mínima":
banco de domínio, skills especialistas, máquina de estados, controle de custo e validação de mídia.

## Estrutura
- `app/domain/` — estados (`states.py`), ids/idempotência/redação (`ids.py`).
- `app/persistence/` — SQLite (`db.py`): migrations + reserva/consumo de cota.
- `migrations/` — schema versionado (`0001_init.sql`).
- `skills/` — skills do Hermes (coordinator, research, ... markdown).
- `config/project.yaml` — configuração do produto (sem código).
- `contentctl.py` — CLI que as skills e o healthcheck chamam.
- `tests/run_tests.py` — testes essenciais (rodam sem pytest).
- `docs/PHASE_A_AUDIT.md` — auditoria nativo × construir.
- `PENDING_OPERATOR.md` — ações que dependem do operador.

## Como rodar (dev)
```
python contentctl.py db-init        # cria/atualiza o banco
python contentctl.py selftest       # roda os testes
python contentctl.py healthcheck    # saúde operacional
```
Banco padrão: `$CONTENT_DB_PATH` (fallback `data/db/content.db`).

## Invariantes
- Fonte da verdade = banco, não o chat.
- Nunca logar segredos (use `ids.redact`). Nunca versionar `.env` ou credenciais.
- Transições de estado sempre validadas. Idempotência por `jobs.input_hash`.
- Sem geração sem cota reservada. Cota grátis esgotada => fallback autorizado / espera / falha controlada.

## Deploy (resumo)
Skills/config vivem em `/data/.hermes/` (volume). Para versionar: fork do template + `entrypoint`
sincroniza `skills/` e `config` do repo para `/data/.hermes/` no boot. Ver `PENDING_OPERATOR.md`.

# content-agent

Operação autônoma de conteúdo coordenada pelo **Hermes Agent** e controlada pelo **Telegram**.
Pesquisa nichos, produz conteúdo em **pt-BR / en / es**, revisa e entrega pelo Telegram.
**Não publica** em redes sociais (fora do escopo do MVP).

## Estado (honesto)
- ✅ Software do MVP pronto, testado (**53 checks**) e **implantado** no Railway a partir deste repo.
- Banco de domínio (11 tabelas), máquina de estados, idempotência, cotas, validação de mídia (ffprobe),
  legendas SRT/VTT, revisão com limite de 2 rodadas, retomada após falha, entrega `MEDIA:`, cron
  (pesquisa/oportunidades/digest/fila/backup) e runner de piloto.
- ⏳ **2 dependências reais** (não-software) para fechar os critérios de aceite — ver `PENDING_OPERATOR.md`:
  1. execução viva do LLM (Nemotron grátis) para pesquisa/roteiro/localização;
  2. operação manual do Google Flow para o vídeo real (sem API paga, sem automação de conta web).

## Documentação
- `docs/OPERACAO.md` — manual de operação (instalar, rodar, pausar/retomar, atualizar, backup/restore, healthcheck, arquitetura).
- `docs/PHASE_A_AUDIT.md` — auditoria do Hermes (nativo × construído).
- `docs/CRITERIOS_ACEITE.md` — checklist do briefing (seção 23) com status honesto.
- `AGENTS.md` — guia do projeto e invariantes.
- `PENDING_OPERATOR.md` — o que depende do operador.

## Rodar (dev)
```
python contentctl.py db-init      # cria/atualiza o banco
python contentctl.py selftest     # 53 checks
python contentctl.py pilot        # piloto 2 ideias x 3 idiomas
python contentctl.py report       # relatório Fase D
```

## Skills (Hermes)
`coordinator · research · opportunity-analysis · scripting · localization · production · review`
(sincronizadas para `/data/.hermes/skills` no boot pelo `scripts/entrypoint.sh`).

Licença/base: template `hermes-railway-template` + imagem oficial `nousresearch/hermes-agent`.

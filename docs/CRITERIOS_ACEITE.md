# Critérios de Aceite do MVP (briefing seção 23) — status honesto

Legenda: [x] atendido • [~] parcial/pronto no software, aguarda execução viva • [ ] pendente

- [x] documentação de instalação do zero testada → `docs/OPERACAO.md` (+ `AGENTS.md`, `docs/PHASE_A_AUDIT.md`)
- [x] sistema funciona na nuvem sem o PC local → Railway, deploy do nosso repo ativo, bot em polling
- [x] Telegram protegido por allowlist → `TELEGRAM_ALLOWED_USERS=8974266170`
- [~] estados e artefatos sobrevivem a reinício → **arquitetado** (volume `/data`, migrations idempotentes, paths no volume) mas **NÃO provado** com dado real sobrevivendo a um restart: o banco do container ainda está vazio (o LLM não rodou), então não há dado gravado a testar contra reinício. Prova pende da execução viva.
- [~] relatório de nichos com fontes e limitações → skill `research` + verbos `source-add`/`niche-add` prontos e testados; **falta execução viva do LLM** para gerar o relatório real
- [~] duas ideias produzidas nos três idiomas → runner de piloto cria 2 ideias × 3 idiomas (6 variantes); legendas reais geradas; **voz real depende do TTS vivo e vídeo do Flow manual**
- [~] seis vídeos passam pela revisão técnica e editorial → pipeline + revisão determinística prontos e testados; **6 vídeos reais dependem do Flow manual** (hoje `aguardando_operacao_flow`)
- [~] cada pacote contém roteiro, legenda, capa e metadados → **legenda (SRT/VTT), capa (SVG 9:16) e metadados-base agora são gerados de verdade** (arquivos reais com hash, testados); o **roteiro/adaptação editorial real** e a redação de título/hashtags localizados **pendem do LLM vivo**. A capa é SVG (rasterização para PNG é opcional, se houver rasterizador no container).
- [x] créditos e custos registrados → `usage_events` + `report` (Fase D)
- [x] limite de revisões funciona → 2 rodadas, depois `bloqueado` (testado)
- [x] falhas provocadas são recuperadas sem duplicar gasto → idempotência por `input_hash` + retomada (testado)
- [x] nenhuma publicação em rede social ocorreu → fora de escopo; não implementado
- [ ] nenhuma credencial versionada ou exposta → **FALHOU e foi corrigido no código**: o token real do bot do Telegram estava **hardcoded** em `tests/run_tests.py` (repo PÚBLICO) — substituído por token fake. Como o token real ficou no **histórico público**, ele está **comprometido**: precisa ser **rotacionado** (ação do operador — ver `PENDING_OPERATOR.md`). O `.env` está no `.gitignore` e `ids.redact` funciona (testado); mas o critério só volta a `[x]` após a rotação.
- [x] funciona na nuvem sem o PC local (revisado) → gateway roda no Railway e o bot **conecta/faz polling** (pending=0, verificado); o **processamento de um turno de LLM não foi verificado ao vivo** (sem rota autorizada de trigger — ver auditoria de execução).
- [x] dependências manuais e limitações documentadas → `PENDING_OPERATOR.md` + este arquivo

## Conclusão honesta
O **software do MVP está pronto, testado (53 checks) e implantado**. Os itens `[~]` não podem ser
marcados como concluídos porque dependem de duas operações que NÃO são software e estão registradas
separadamente em `PENDING_OPERATOR.md`:
1. **Execução viva do LLM** (Nemotron grátis) — para pesquisa, roteiro e localização reais.
2. **Operação manual do Google Flow** — para os 6 vídeos reais (sem API paga, sem automação de conta web).

Enquanto essas duas não rodarem com evidência (arquivos reais + validação de mídia), o MVP **não** é
declarado concluído.

# PENDING_OPERATOR — o que só o Carlos pode fazer

## 🔴 URGENTE — ROTACIONAR O TOKEN DO BOT DO TELEGRAM (credencial comprometida)
Durante a auditoria encontrei o **token real do bot hardcoded** em `tests/run_tests.py` num repo **PÚBLICO**.
Já corrigi o código (troquei por token fake), mas o token real **ficou no histórico público do git** →
considere-o **comprometido**. Ação (só você):
1. No Telegram, fale com **@BotFather** → `/revoke` (ou `/token`) no bot `@meu_hermes_agente01_bot` para
   gerar um token novo. Isso invalida o antigo imediatamente.
2. No Railway (serviço) → Variables → atualize `TELEGRAM_BOT_TOKEN` com o novo valor. O bot reconecta.
(Também revogue, quando puder, os tokens que usei nesta sessão: o Railway API token e o GitHub PAT — ficaram
só em memória, nunca em arquivo, mas a boa prática é revogar.)

## 🎯 AS 2 DEPENDÊNCIAS REAIS RESTANTES (o software está pronto e testado; falta operação)
1. **Execução viva do LLM (Nemotron grátis).** A lógica de pesquisa/roteiro/localização está pronta e
   testada, mas só produz conteúdo REAL quando o bot roda o LLM. **Auditei se havia rota autorizada para
   disparar isso agora com acesso já configurado — NÃO há** (evidência técnica):
   - o cron de pesquisa vive no CONTAINER (o `hermes` local é outra instância, com outros jobs);
   - o serviço não expõe HTTP (bot é polling) → sem trigger via HTTP;
   - a API do Railway só faz build/deploy, não exec;
   - o único exec no container (`railway ssh`) exige **registrar uma chave SSH nova** (não existe nenhuma) →
     isso é provisionar acesso novo, fora do que você autorizou, então **não fiz**;
   - mandar mensagem ao bot dispararia o LLM, mas você pediu para eu **não** mandar mensagens por você.
   **Ações possíveis (sua escolha):** (a) mandar 1 mensagem ao bot pedindo a pesquisa (grátis); (b) esperar
   o cron de domingo 9h; (c) se quiser que EU dispare via `railway ssh`, autorize registrar uma chave SSH
   na conta Railway (aí eu rodo `hermes cron run content-weekly-research` sem gasto).
2. **Operação manual do Google Flow (vídeo).** Sem via automatizada autorizada. Cada cena fica em
   `aguardando_operacao_flow` com ordem de trabalho (`contentctl.py flow-order`). Gere no Flow, baixe e
   informe os caminhos. API Veo (paga) desabilitada por padrão — exigiria sua decisão de gasto.

## ⚙️ Recomendado (defesa contra o "drift_skip" — sem gasto)
Os crons `content-*` são criados **sem fixar modelo** e o container **não tem `LLM_MODEL`** definido. O
mecanismo `drift_skip` do Hermes **pula crons não fixados** quando o modelo global muda (silenciosamente,
sem produzir nada). Para blindar (já deixei o entrypoint pronto para isso), defina no Railway → Variables:
- `CONTENT_CRON_PROVIDER=openrouter`
- `CONTENT_CRON_MODEL=nvidia/nemotron-3.5-lightning:free`  (o modelo grátis validado)
No próximo deploy o entrypoint fixa os 4 crons de agente nesse modelo. (Se o provider/modelo real diferir,
ajuste esses dois valores — nada mais muda.)



> Este arquivo é a lista SEPARADA que o operador pediu. O agente continua tudo o que
> consegue sozinho; aqui ficam apenas ações/decisões que exigem contas, acessos ou escolhas.
> Marcações: [ ] pendente • [x] resolvido.

## 🔴 BLOQUEIO ATUAL (22/09, fim do dia): Railway workspace RESTRINGIDO
- [ ] O Railway retornou: **"Your workspace has been restricted. Please attach a payment method or
      contact support to resolve this."** O trial gratuito ($5/30 dias) foi esgotado/sinalizado.
      **Efeito:** nenhum deploy roda — todos viraram REMOVED e o **bot está fora do ar** até você resolver.
      **Só você resolve** (decisão de conta/pagamento). Opções:
      1. Anexar método de pagamento no Railway (Settings → Billing) — decisão de gasto (você pediu "pergunto antes").
      2. **Pivotar o deploy para a VPS Hostinger** (o alvo real do briefing) — também é compra, decisão sua.
      3. Deixar o código como está (100% pronto) e decidir a infra depois.
- [ ] Observação: o `serviceConnect` via API reportou sucesso mas NÃO repontou o serviço (continuou no
      upstream `lovexbytes`); repontar de forma confiável é pela dashboard (Settings → Source) — mas isso
      só importa depois que a restrição do workspace for resolvida.

## Bloqueia a IMPLANTAÇÃO (deploy no Railway) — resolver antes de subir skills
- [ ] **Token clássico do GitHub** (1 minuto): os tokens fine-grained (`github_pat_...`) não conseguem
      criar/forkar repo e só enxergam repositórios pré-selecionados — travaram a automação em 22/09.
      Gerar em github.com/settings/tokens → **Generate new token (classic)** (valor começa com `ghp_`)
      → escopo **`repo`** → colar no chat. Com ele o agente cria o repo, sobe o código e reaponta o Railway sozinho.
- [ ] (Alternativa) Criar o repo `hermes-content-agent` **e** gerar o token fine-grained com
      **Repository access = All repositories** + **Contents: Read and write** (senão o token não enxerga o repo novo).
- [ ] Depois do repo no ar: o agente estende o `entrypoint.sh` (fork) para sincronizar `skills/` e `config`
      para `/data/.hermes/` no boot, e reaponta o serviço do Railway para o novo repo.

> Estado em 22/09: código versionado LOCALMENTE em `C:\Users\carlo\Documents\ACHADINHOS\hermes-content-agent`
> (commit feito). Falta só publicar no GitHub + reapontar o Railway — não bloqueia continuar o desenvolvimento.

## Decisões de produto (não bloqueiam a base; têm default seguro de desenvolvimento)
- [ ] Países-alvo de **inglês** e **espanhol** (hoje: linguagem internacional neutra).
- [ ] Nichos **proibidos** extras além dos já vetados (médico/jurídico/financeiro/político).
- [ ] **Provedor de voz** preferido (default de dev: Edge TTS grátis).
- [ ] Formato visual/identidade dos canais.
- [ ] Volume mensal desejado após o piloto.

## Contas e credenciais (fornecer só na hora da integração; nunca colar em arquivo versionado)
- [ ] **Provedores de LLM grátis** a validar no ambiente real (NVIDIA, Qwen/DashScope, etc.) — nomes de
      variável já mapeados no `.env.example`.
- [ ] **Google Flow:** definir a **via permitida** de operar as 5 contas (ver risco abaixo).
- [ ] **Programas de afiliados**: só usaremos links reais de contas autorizadas suas (nenhum inventado).
- [ ] **Telegram:** IDs numéricos autorizados (allowlist) e, se quiser, grupo/tópicos dedicados.

## Riscos que podem exigir sua decisão de gasto
- [ ] **Google Flow × API Veo:** créditos do produto web provavelmente NÃO são usáveis via API (faturamento
      separado). Se quisermos vídeo automático, ou o Flow vira **etapa manual** (`aguardando_operacao_flow`),
      ou entra a **API Veo paga** (dólar/segundo) — o que exige sua autorização de gasto. Confirmo na prova técnica.
- [ ] **VPS Hostinger:** antes de contratar, o agente apresenta plano + custo; a **compra é sua** (o agente não compra).

## Segurança
- [ ] Depois que tudo estiver no ar, **revogar o token do Railway** usado para a configuração inicial.

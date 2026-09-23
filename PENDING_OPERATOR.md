# PENDING_OPERATOR — o que só o Carlos pode fazer

## 🎯 AS 2 DEPENDÊNCIAS REAIS RESTANTES (o software está pronto e testado; falta operação)
1. **Execução viva do LLM (Nemotron grátis).** A lógica de pesquisa/roteiro/localização está pronta e
   testada, mas só produz conteúdo REAL quando o bot roda o LLM — o que acontece quando você manda uma
   mensagem ao bot no Telegram OU no cron de domingo. Ação: mandar 1 mensagem ao `@meu_hermes_agente01_bot`
   pedindo a pesquisa de nichos (não é gasto — o modelo é grátis). Sem canal meu para disparar o LLM do bot.
2. **Operação manual do Google Flow (vídeo).** Não há via automatizada autorizada (créditos do produto
   Flow provavelmente não rodam na API Veo; automatizar a web fere termos). Cada cena fica em
   `aguardando_operacao_flow` com ordem de trabalho (`contentctl.py flow-order`). Ação: gerar as cenas no
   Flow manualmente, baixar e informar os caminhos ao sistema. Alternativa paga (API Veo) exige sua
   decisão de gasto — hoje NÃO usada.


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

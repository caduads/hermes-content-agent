# PENDING_OPERATOR — o que só o Carlos pode fazer

> Este arquivo é a lista SEPARADA que o operador pediu. O agente continua tudo o que
> consegue sozinho; aqui ficam apenas ações/decisões que exigem contas, acessos ou escolhas.
> Marcações: [ ] pendente • [x] resolvido.

## Bloqueia a IMPLANTAÇÃO (deploy no Railway) — resolver antes de subir skills
- [ ] **Forkar** `lovexbytes/hermes-railway-template` para a sua conta do GitHub e, no serviço do
      Railway (Settings → Source), **trocar a origem** para o seu fork. Sem isso não dá para versionar
      e reimplantar nossas skills. (O agente prepara o `entrypoint` de sincronização assim que o fork existir.)
- [ ] Dar ao agente **acesso de push** ao fork (ou você aplica os commits que o agente preparar).

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

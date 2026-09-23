# PENDING_OPERATOR — o que só o Carlos pode fazer

> Este arquivo é a lista SEPARADA que o operador pediu. O agente continua tudo o que
> consegue sozinho; aqui ficam apenas ações/decisões que exigem contas, acessos ou escolhas.
> Marcações: [ ] pendente • [x] resolvido.

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

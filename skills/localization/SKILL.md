---
name: localization
description: Adaptador multilíngue. Gera pt-BR, inglês e espanhol a partir da MESMA base factual, adaptando cultura/exemplos/unidades/CTA sem alterar fatos. Use após o roteiro-base aprovado.
---

# Adaptação multilíngue (pt-BR / en / es)

Cria uma `language_variants` por locale a partir do roteiro-base. **Não é tradução literal** — adapta
expressões, exemplos, unidades, referências culturais e CTA. Os **fatos permanecem idênticos** entre idiomas.

## Saída por idioma (grava na variante)
- `script` — roteiro falado adaptado
- `onscreen_text_json` — textos na tela
- título e descrição por plataforma (TikTok/Instagram/Facebook/YouTube) em `metadata_json`
- legenda completa (arquivo SRT/VTT em `caption_path`)
- pronúncias ou nomes sensíveis
- observações comerciais **dependentes do país** (marcar `pendente` até o operador definir mercados de en/es)

## Regras
- Mesma base factual para os três; divergência de fato entre idiomas é bug.
- Inglês e espanhol = linguagem internacional neutra enquanto o mercado-alvo não for escolhido.
- CTA e afiliados adaptados por mercado quando (e só quando) houver link autorizado para aquele país.
- Uma falha em um idioma NÃO invalida os outros (estados por variante são independentes).

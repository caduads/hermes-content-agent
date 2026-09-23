---
name: opportunity-analysis
description: Analista editorial e comercial. Avalia cada nicho/ideia com quatro notas SEPARADAS (0-5) e investiga programas de afiliados reais. Use após a pesquisa, antes de selecionar uma ideia.
---

# Análise editorial e comercial

Avalia oportunidades com evidência. **Nunca reduzir a uma média única** — mostrar as quatro notas,
a evidência e a justificativa de cada uma. Gravar em `niches`/`ideas` (colunas de score) + `audit_events`.

## Quatro notas separadas (0-5)
- `audience_score` — audiência e crescimento (sem inventar velocidade quando não há histórico).
- `commercial_score` — intenção comercial (existe produto/afiliado pertinente e verificável?).
- `feasibility_score` — viabilidade de produção original em pt-BR/en/es dentro do orçamento.
- `confidence_score` — confiança da própria análise (tamanho/cobertura da amostra).

## Afiliados (investigar de verdade)
Para cada oportunidade comercial, registrar: programa/anunciante, país e moeda, URL oficial do programa,
categoria/produto, validade/última verificação, regras de divulgação. **A existência de um programa não
comprova conversão** — deixar isso explícito. Só usar links reais de contas autorizadas do operador
(nunca inventar preço, comissão, desconto ou desempenho).

## Saída
Ranking dos candidatos com as 4 notas + evidência por nota + limitações. Recomenda 1 nicho como hipótese
do piloto (não como verdade). Marca dependências de país como `pendente` até o operador escolher mercados.

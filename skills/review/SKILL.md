---
name: review
description: Revisor técnico e editorial. Verifica fatos, coerência entre idiomas, naturalidade, áudio, legendas, cenas, mídia e originalidade. Máximo 2 rodadas automáticas de correção; depois marca 'bloqueado'. Use quando a variante entra em 'revisando'.
---

# Revisão técnica e editorial

Avalia cada variante de idioma antes da entrega. Grava o resultado em `language_variants.review_json` e
incrementa `revision_count`. **Não aprovar uma saída apenas pelo modelo que a produziu** — usar regras
determinísticas (ver validação de mídia) e, quando possível, um revisor distinto.

## Checklist
- fatos e fontes conferidos
- coerência entre os três idiomas (fatos idênticos)
- naturalidade linguística (sem tradução artificial)
- clareza e pronúncia da voz
- áudio sem cortes/sobreposição indevida
- legendas completas, legíveis e sincronizadas (nenhum segmento fora da duração)
- coerência e continuidade visual das cenas
- ausência de marca d'água indevida
- duração, proporção (9:16) e codificação corretas (validação automática)
- originalidade e valor editorial próprio
- identificação de afiliado quando aplicável (regras de divulgação da plataforma)

## Limite de correções
Devolve a variante para no máximo **2 rodadas automáticas** de correção (`MAX_AUTOMATIC_REVISIONS`).
Esgotado o limite, marca a variante como **`bloqueado`** e explica a causa no Telegram (tópico Custos e falhas),
sem loop infinito. Aprovada, transiciona para `pronto`.

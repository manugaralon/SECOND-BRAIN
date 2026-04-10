# Knowledge Base Entry Schema

## Required Fields

Every KB entry must include exactly these 6 fields in its YAML frontmatter:

```yaml
concept: string       # Kebab-case slug, unique identifier. Example: "escoliosis-lumbar-diagnostico"
domain: enum          # One of: fisioterapia | ia | finanzas | trading | esoterismo | psicologia | deportes | personal
confidence: float     # Range 0.0-1.0 (see confidence scale below)
summary: string       # One sentence describing what this entry asserts
sources: list         # Each item has either note: "notes/slug.md" or url: "https://...", plus date: "YYYY-MM-DD"
last_updated: date    # Format: "YYYY-MM-DD"
```

## Optional Fields

These 3 field groups are omitted when not applicable — do not write empty arrays:

```yaml
contradicts:          # list of {concept: string, detail: string}
extends:              # list of {concept: string}
gaps:                 # list of strings describing unknowns
```

## Confidence Scale

| Value | Meaning |
|-------|---------|
| 0.9+  | Multiple independent sources agree, no contradictions |
| 0.7-0.9 | Single high-quality source, or multiple weak sources agreeing |
| 0.5-0.7 | Contested, single influencer source, or unverified claim |
| below 0.5 | Explicitly contradicted or speculative |

## File Naming Convention

- Kebab-case of concept name
- No domain prefix
- No UUID
- Qualifier suffix for multi-aspect concepts

Examples:
- `escoliosis-lumbar-diagnostico.md`
- `pies-planos-tipo.md`
- `prompting-chain-of-thought.md`
- `escoliosis-lumbar-restricciones.md` (qualifier suffix for related aspect)

## Directory Structure

- `kb/concepts/` — all domain knowledge, flat
- `kb/personal/` — personal context entries
- No subdirectories by domain until corpus exceeds ~100 entries
- The `domain` frontmatter field handles filtering — filesystem structure does not

## Example Entry

```yaml
---
concept: "escoliosis-lumbar-diagnostico"
domain: "personal"
confidence: 0.9
summary: "Manuel tiene escoliosis lumbar diagnosticada"
sources:
  - note: "manual-input"
    date: "2026-04-10"
last_updated: "2026-04-10"
contradicts:
  - concept: "otro-concepto"
    detail: "Lo que específicamente contradice"
extends:
  - concept: "perfil-fisico-general"
gaps:
  - "Severidad exacta de la curvatura no documentada"
  - "Tratamiento actual desconocido"
---

- Escoliosis lumbar diagnosticada
- Región afectada: columna lumbar
- Afecta la selección de ejercicios y posturas
```

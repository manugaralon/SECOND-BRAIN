# Second Brain — El Oráculo

## What This Is

Un sistema de conocimiento personal adaptativo que ingiere contenido heterogéneo (vídeos, imágenes, posts de Instagram, URLs), lo sintetiza en una base de conocimiento atómica y estructurada, y actúa como oráculo: razona sobre todo lo que sabe — incluyendo el contexto personal de Manuel — para responder preguntas de forma integrada y personalizada. La interfaz es Claude Code en el MVP.

## Core Value

Cuando preguntas sobre un tema, recibes conocimiento sintetizado y personalizado a tu caso — no una lista de notas.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] El sistema ingiere links (Instagram reels, posts, carruseles) y los convierte en notas .md estructuradas
- [ ] Las notas se procesan en entradas atómicas de conocimiento con esquema estándar (concepto, dominio, confianza, fuentes, contradicciones, gaps)
- [ ] El contexto personal de Manuel (escoliosis, pies planos, otros datos) vive en la KB como conocimiento más, no como perfil separado
- [ ] El sistema detecta cuando nueva información contradice conocimiento existente y lo señala explícitamente
- [ ] El sistema detecta gaps: "sobre X hay poco conocimiento acumulado"
- [ ] Claude Code puede consultar la KB y responder preguntas sintetizadas y personalizadas
- [ ] El flujo ingest → KB es reproducible y fácil de ejecutar cuando llegan nuevos links

### Out of Scope

- Interfaz web — se construye en fase posterior si la necesidad es clara
- ChromaDB / búsqueda semántica — se añade cuando el corpus supere ~100 conceptos
- Ingesta automática (sin intervención manual) — demasiado complejo para MVP
- Multi-usuario — sistema personal, no transferible en contenido

## Context

- El pipeline de ingesta ya existe: `transcribe.py` (yt-dlp + Groq Whisper para vídeo, Llama 4 Vision para imágenes/carruseles) → produce `notes/*.md` con frontmatter
- Las `notes/*.md` son el output del pipeline, no el destino final — la KB son entradas atómicas derivadas de esas notas
- Los dominios de interés: fisioterapia (escoliosis, pies planos, cadenas miofasciales), IA/prompting, finanzas, trading, esoterismo, psicología, sociología, deportes
- El contexto personal (condición física, situación, historial) se ingiere como conocimiento igual que cualquier otro contenido
- Claude Code es la interfaz de consulta en el MVP — lee la KB y razona sobre ella

## Constraints

- **Stack**: Python 3.12+, Groq API (Whisper + Llama 4 Vision), archivos .md como capa canónica
- **Sin UI**: MVP es CLI + consulta vía Claude Code
- **Personal**: el contenido de la KB no es transferible — solo el mecanismo lo es
- **Pipeline existente**: no reescribir lo que ya funciona, construir encima

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| KB como .md atómicos, no ChromaDB | Corpus insuficiente para justificar infra; .md es suficiente hasta ~100 conceptos | — Pending |
| Contexto personal = conocimiento, no perfil separado | El oráculo razona holísticamente; separar el perfil crea una distinción artificial | — Pending |
| Claude Code como interfaz MVP | Ya existe, funciona, no requiere UI; ampliar después si hay necesidad clara | — Pending |
| Pipeline de ingesta reutilizado | Ya funciona para 14/14 posts; construir encima, no reescribir | — Pending |

---
*Last updated: 2026-04-08 after initialization*

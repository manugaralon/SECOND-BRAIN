# 🧠 Second Brain — Home

> Base de conocimiento personal de Manuel. Usa [[INDEX]] para el índice completo.

---

## 📊 Estado de la KB

```dataview
TABLE length(rows) AS "Entradas"
FROM "concepts" OR "personal"
GROUP BY domain
SORT length(rows) DESC
```

---

## 🤖 IA

```dataview
TABLE summary, confidence
FROM #ia
SORT confidence DESC
```

---

## 💰 Finanzas & Trading

```dataview
TABLE summary, confidence
FROM #finanzas OR #trading
SORT confidence DESC
```

---

## 🧠 Psicología & Sociología

```dataview
TABLE summary, confidence
FROM #psicologia OR #sociologia
SORT confidence DESC
```

---

## 🏃 Fisioterapia & Deportes

```dataview
TABLE summary, confidence
FROM #fisioterapia OR #deportes
SORT confidence DESC
```

---

## ✨ Esoterismo

```dataview
TABLE summary, confidence
FROM #esoterismo
SORT confidence DESC
```

---

## 👤 Personal

```dataview
TABLE summary, confidence
FROM #personal
SORT file.name ASC
```

---

## ⚠️ Entradas con baja confianza

```dataview
TABLE domain, confidence, summary
FROM "concepts" OR "personal"
WHERE confidence < 0.5
SORT confidence ASC
```

---

## 🕳️ Entradas con gaps documentados

```dataview
TABLE domain, gaps, confidence
FROM "concepts" OR "personal"
WHERE gaps
SORT domain ASC
```

---

## 🕒 Actualizadas recientemente

```dataview
TABLE domain, summary, last_updated
FROM "concepts" OR "personal"
SORT last_updated DESC
LIMIT 10
```

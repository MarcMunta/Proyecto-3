---
version: 1
slug: "src-app-tsx"
primary_target: "src/App.tsx"
related_targets: []
---

## Scope

Single-page app `frontend/` — interactive map of Spain for CPD viability and profitability. Visitor mode: Operate. Projected in the defence and used on laptop/phone. Audience: master's tribunal + investor.

User steers: (13/11) "mapa de España interactivo con las provincias y las zonas de las provincias"; (13/11, later, relayed by the parent session) "Improve the interface: more visual, use a red / orange / yellow / green palette to represent profitability, and make it more minimalist and pretty."

## Direction contract

THESIS: A map where colour means profitability and nothing else: each province reads green, yellow, orange or red at a glance. Refuses dashboards of cards, borders and labels.

OWN-WORLD: near-black ground #111214, warm ink #f1ecdf; validated profitability palette (#40b97a, #dcbc55, #e47b2f, #b8383f) only on map, legend, class badge and distribution bar; ordinal bar icon per class; hatching = no data; Martian Mono numerals that roll in; Archivo prose; soft radii; hairlines only.

STORY: see which provinces pay off, click one, the map dives to its municipalities, the panel shows the class, three big numbers (VAN, ROI, payback) and small bars for power, climate, water and market, then the reasons.

FIRST VIEWPORT: thin header (title, live power price, demo seal only on fallback); map ~64% left with compact legend and Canarias inset; right panel with title, distribution bar and list grouped by class.

FORM: user-pinned refinement of the Tablero de Salidas world (seed bbe2ce6f), 13/11/2026.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Data

Real per-province prediction `data/curated/predicciones_provincia.json` (served by a Vite plugin) when present; otherwise the synthetic demo model with a visible seal and a documented relative class rule (No viable → no rentable; rest by VAN tertiles).

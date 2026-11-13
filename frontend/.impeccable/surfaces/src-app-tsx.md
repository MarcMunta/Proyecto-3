---
version: 1
slug: "src-app-tsx"
primary_target: "src/App.tsx"
related_targets: []
---

## Scope

Single-page app `frontend/` — interactive map of Spain for CPD viability. Visitor mode: Operate (evaluate a province), projected in the defence and used on laptop/phone. Audience: master's tribunal + investor.

User steer (chat, 13/11/2026): "Quiero que sea el mapa de España de forma interactiva con las provincias, las zonas de las provincias y etc" → map is the protagonist; zooming into a province reveals its real municipalities.

## Direction contract

THESIS: Spain as a departures board: every province is a destination announced with status, score and the time of its data. Refuses the dark dashboard of glass KPI cards.

OWN-WORLD: matte black flap modules with hairline joints, warm-white split-flap characters in condensed Martian Mono, Archivo for prose; status lamps green/orange/red each with its own glyph; board yellow only for the active province; zero radius, 1px rules; warm luminance ramp for score; hatching means no data.

STORY: the visitor sees which provinces "depart" (viable), clicks one, the map dives to its municipalities and the board flips its figures: verdict, reasons, CAPEX/OPEX/VAN, live power price and weather.

FIRST VIEWPORT: top strip with clock, live spot price and demand; full-bleed map left 62% with Canarias inset; departures board right 38%; action = click a province or a row.

FORM: Departures board (split-flap), position 7/7, seed bbe2ce6f.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- Province aggregation of the future real master table (best site vs. average): show both.

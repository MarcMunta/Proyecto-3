# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated (the brief said "pick a modern stack yourself"): Vite + React + TypeScript, MapLibre GL JS for the map (WebGL, smooth camera, data-driven styling from a static GeoJSON, no API key or tile token needed). Python export script reuses the repo's own model (`src/cpd/scoring.py`) to write the JSON the frontend reads.

## Users

Two audiences, confirmed equally important:

- **Tribunal of the Màster FP IA i Big Data (Stucom)** evaluating Proyecto 3: they judge methodology, which data is real vs. synthetic, and clarity of the reasoning.
- **A company or investor deciding where in Spain to build a CPD (data center)**: they read figures, profitability and risks.

Viewing scene, confirmed: both projected on a large screen during the project defence and used up close on a laptop (and usable on a phone).

## Product Purpose

Interactive map of Spain that answers "how viable and how profitable would a CPD be here?" per province. Click a province, the map zooms in, and a panel shows viability state (Viable / Viable con condiciones / No viable), a 0-100 score with its reasons, CAPEX, OPEX, VAN, ROI, payback, electricity price, water, climate (PUE / free cooling), CO2, latency and other features. Live data (electricity price, demand, renewable share, weather) where available, always with its timestamp. Success: a viewer understands within seconds which provinces are promising and why, and can trust which numbers are real.

## Positioning

It runs the project's own 10-model viability funnel (filters M1-M10, sub-scores, financial simulator) and puts its output next to live official feeds (Red Eléctrica REData, Open-Meteo). It shows its reasons, not just a colour.

## Operating Context

- Owner: self-taught student developer; delivery 15/12/2026.
- Data pipeline is in progress in a parallel workstream: today the model runs on `data/demo/municipios_demo.csv` (28 municipalities, SYNTHETIC indicators with real names, INE codes and coordinates). A real master table will replace it later; the frontend must regenerate from the same export script.
- Live feeds verified without keys (13/11/2026): REData demand and market prices (national, peninsular), REData renewable share / CO2, Open-Meteo current weather. ESIOS and AEMET need keys and are not used.

## Capabilities and Constraints

- UI text in Spanish.
- Never invent values: provinces without model data show "sin datos todavía".
- Synthetic numbers carry a visible "datos de demostración" mark.
- National electricity price and demand are labelled as national (peninsular), not per province.
- No API keys or secrets in the repo.
- Canarias must be reachable (inset or camera jump); Baleares, Ceuta and Melilla present.
- Undecided: how the real master table will aggregate to provinces (best municipality vs. average); the frontend shows both.

## Evidence on Hand

- Model output from `src/cpd/scoring.py::evaluar()` over the demo CSV (synthetic indicators).
- Province geometry: Eurostat GISCO NUTS-3 2024 (real).
- Live REData and Open-Meteo responses (real).
- No customers, testimonials, real site prices or benchmarks exist; none may be fabricated.

## Product Principles

1. Honesty over polish: every number says whether it is live, modelled or synthetic.
2. Reasons beside verdicts: a score is never shown without the motives that produced it.
3. One click to the answer: province → zoom → verdict, figures and reasons, no hunting.
4. Readable at projector distance and at arm's length alike.

## Accessibility & Inclusion

Keyboard-operable map selection (province list/search), sufficient contrast for projection, respects reduced motion, state never encoded by colour alone.

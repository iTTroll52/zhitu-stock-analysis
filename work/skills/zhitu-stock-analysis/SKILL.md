---
name: zhitu-stock-analysis
description: Analyze or screen one or more eligible Shanghai/Shenzhen main-board A-shares with Zhitu Data Service APIs, primary disclosures, global-market context, sector-rotation positioning, conditional stock candidates, and model-portfolio position ranges. Use for realtime snapshots, batch candidate screening, limit-up opportunity research, review, fundamentals, industry position, evidence quality, overseas risk transmission, current sector-rotation stage, candidate reasons, staged entries, and invalidation-aware exposure planning with a user-provided Zhitu API token. Excludes ChiNext, STAR Market, ST/*ST, and other stocks outside the user's tradable main-board universe by default.
---

# 智兔股票分析

Use Zhitu for structured market data and use primary sources for claims that Zhitu cannot prove. Treat every ranking as a research-priority model, never as a promise of profit or a personalized trade instruction.

Never expose a token in browser code, commands shown to the user, logs, generated files, or the final response. Read it from the server-side environment variable `ZHITU_API_TOKEN`.

For a safe entitlement smoke test, run `python scripts/test_connection.py`. The script reads only `ZHITU_API_TOKEN`, tests four low-frequency read-only endpoint families, and prints counts/status without response contents or the token.

Run `python scripts/data_quality.py <kind> <json-file>` to validate saved `quote`, `stock-list`, or `financial-ratios` payloads before using them in analysis.

## Required references

Read these files before acting:

1. [references/zhitu-api.md](references/zhitu-api.md) for endpoint selection, cadence, and limitations.
2. [references/analysis-framework.md](references/analysis-framework.md) for scoring, evidence gates, and outputs.
3. [references/data-quality-gates.md](references/data-quality-gates.md) before accepting API, financial, historical, or backtest data.
4. [references/global-risk-overlay.md](references/global-risk-overlay.md) for every analysis; keep the block compact for long-horizon fundamental work but never omit the data cutoff, overseas session state, or transmission assessment.
5. [references/sector-rotation.md](references/sector-rotation.md) for every single-stock analysis, batch screen, market review, or short-horizon outlook.
6. [references/rotation-candidates-and-positioning.md](references/rotation-candidates-and-positioning.md) whenever the user requests stocks corresponding to a rotation, entry conditions, position size, an aggressive/balanced/conservative plan, or a trade-oriented shortlist.

## Hard tradability gate

Apply this gate before fetching expensive data or ranking candidates:

- Default eligible universe: Shanghai and Shenzhen **main-board A-shares only**.
- Allow common Shanghai main-board prefixes `600`, `601`, `603`, `605` and Shenzhen main-board prefixes `000`, `001`, `002`, `003`, subject to instrument metadata confirmation.
- Exclude ChiNext prefixes `300` and `301`.
- Exclude STAR Market prefixes `688` and `689`.
- Exclude every name or code returned by the current ST list, including `ST`, `*ST`, delisting-risk, or equivalent special-treatment labels.
- Exclude BSE and any instrument outside the confirmed Shanghai/Shenzhen main-board universe unless the user explicitly changes the universe and confirms trading permission.

An excluded stock receives no opportunity score. Return the exact exclusion reason. Never allow technical strength, theme heat, or a limit-up record to override this gate.

## Inputs

Accept:

- one stock code for a full diagnostic;
- several codes for comparison;
- a market-wide or sector screen;
- a requested horizon: intraday observation, next session, 2–5 sessions, swing, or fundamental research.

Normalize symbols and confirm board/type with instrument metadata where possible. Split realtime multi-symbol requests into batches of at most 20. If no token is available, produce the request plan and evidence checklist without inventing live values.

## Workflow

1. **Set the target.** Define one outcome and horizon. Keep `next-session limit-up`, `next-session positive return`, and `five-session excess return` as separate labels.
2. **Apply the tradability gate.** Remove ineligible boards and ST/*ST before ranking.
3. **Apply the data-quality gate.** Validate shape, fields, units, freshness, formulas, missing-value reasons, adjustment method, and point-in-time availability using [references/data-quality-gates.md](references/data-quality-gates.md). Stop scoring on hard errors or a score below 80.
4. **Reconcile material data.** Compare realtime endpoint families within the same source-time window. Verify key financial values with an independent source and use the original filing to resolve differences above 5%.
5. **Build the mandatory market and rotation pack.** For every analysis, report core-index direction, multi-period trend, total-market liquidity versus comparable windows, breadth, limit-up/down/broken-board structure, style, current market regime, and sector concentration. Classify sectors by rotation stage using [references/sector-rotation.md](references/sector-rotation.md); report which sectors are leading, strengthening, diverging, fading, or only candidates for observation.
6. **Add the mandatory global overlay.** For every analysis, assess US, Japanese, Korean, Hong Kong, commodity, FX, rate, overseas-policy, and geopolitical transmission using [references/global-risk-overlay.md](references/global-risk-overlay.md). Timestamp every observation and identify whether each market is intraday, closed, or from the prior session.
7. **Create a data-only pre-screen.** Use liquidity, relative strength, turnover, trend, limit-up structure, sector breadth, and risk flags only to narrow research candidates. Label it `pre-screen`, not a final recommendation.
8. **Verify the business case.** For every surviving candidate, inspect filings, financial statements, official website disclosures, and investor-relations/research records. Quantify industry position, catalyst-related revenue share, earnings elasticity, validated orders, and validated capacity.
9. **Build conditional candidates and exposure.** When requested, map confirmed rotation stages to eligible main-board candidates and produce a model-portfolio exposure plan using [references/rotation-candidates-and-positioning.md](references/rotation-candidates-and-positioning.md). Separate `initial`, `confirmation`, and `maximum` exposure; include entry, no-chase, reduction, and invalidation conditions.
10. **Apply evidence gates and score caps.** Missing primary evidence must reduce the score. Theme heat cannot compensate for missing fundamentals or unverified commercial claims.
11. **Challenge the thesis.** State the strongest bearish explanation, invalidation conditions, crowded-trade risk, event expectations already priced in, and data gaps.
12. **Return timestamped output.** Separate facts, calculations, inferences, and unknowns. Show data-quality score before the stock score and cite primary evidence close to each material claim.

## Analysis modes

### Single stock

Return:

1. eligibility result;
2. data cutoff, quality score, quality flags, sources, and adjustment method;
3. price/liquidity snapshot and source/fetch timestamps;
4. mandatory market/global dashboard: core indices, liquidity, breadth, style, overseas session state, rates/FX/commodities, and transmission to A shares;
5. sector-rotation position: the target sector's stage, current leaders, strengthening sectors, fading sectors, and evidence against the classification;
6. fundamentals and industry position;
7. revenue exposure, earnings elasticity, order validation, and capacity validation;
8. evidence coverage table;
9. technical/flow observations;
10. bullish case, bearish case, invalidation conditions, and missing evidence;
11. transparent component scores, caps applied, and final research tier.

### Batch screen

Use two stages:

1. `Market-data pre-screen`: eligible universe, liquidity, relative strength, sector breadth, limit-up/down structure, and abnormal-risk filters.
2. `Research validation`: primary-source evidence and fundamental scoring for the smaller survivor set.

Before ranking stocks, show the mandatory market/global dashboard and a sector-rotation table with current leaders, newly strengthening groups, crowded/diverging groups, fading groups, and unconfirmed watch candidates. Show excluded symbols separately with reasons. Never publish a high-conviction list based only on price/volume or theme heat. If the batch is too large for primary-source verification, return a shortlist and mark every unverified name `pending research validation`.

### Rotation candidates and position planning

When the user asks which stocks correspond to the current rotation or how much exposure to use:

1. re-run the current instrument/ST gate and data-quality gate;
2. classify the market and each sector before naming stocks;
3. include only candidates with a verifiable role such as leader, liquid bellwether, fundamental confirmation, or newly strengthening adjacent-chain candidate;
4. show primary reasons and counter-evidence, not just theme labels;
5. express exposure as model-portfolio percentages, never as certainty or a substitute for the user's suitability assessment;
6. provide initial, confirmation, and maximum ranges plus staged-entry and invalidation rules;
7. lower exposure or return only a watchlist when live snapshots, current ST data, comparable intraday windows, or primary evidence are missing.

### Review / 复盘

For daily review, compare the prior thesis with the close:

- which sectors supplied limit-ups, down-limits, and broken boards;
- whether breadth expanded or narrowed and whether leaders were one-day rotations or showed multi-day confirmation;
- where each material sector moved in the rotation sequence and whether the prior `starting/strengthening/accelerating/diverging/fading` label was confirmed;
- whether volume, sector follow-through, filings, orders, capacity, or overseas events confirmed the thesis;
- which signals were false positives and why;
- whether score thresholds or features need backtest review, without changing rules merely to fit one day.

## Integrity rules

- Do not call vendor dynamic PE `TTM` unless independently confirmed.
- Do not infer causation from co-movement with an overseas index.
- Do not treat capital flow, chip distribution, five-level quotes, limit-up pools, or technical indicators as proof of future returns or complete Level-2 data.
- Do not describe planned capacity as commissioned capacity, a framework agreement as an order, an order as recognized revenue, or an industry TAM as company revenue exposure.
- Avoid look-ahead bias. Use only evidence available before the prediction cutoff.
- Never convert missing, permission-denied, stale, or API-error fields to zero. Keep the reason code and lower data quality.
- Preserve period end, first disclosure, revision, fetch, and model-availability times. Do not overwrite historical values with later restatements.
- Do not use a payload that fails deterministic formula/schema checks. Do not average conflicting snapshots before comparing source timestamps.
- Do not claim `high probability` until a fixed rule has out-of-sample results with sample size, base rate, cutoff time, costs, limit-up fill assumptions, and confidence interval. Otherwise use `higher research priority` or `signal score`.

## Operations

- The all-market realtime endpoint is eligible-plan dependent, updates about once per minute, and should not be requested more than once per minute.
- Cache universe/ST lists daily; financials, profiles, holders, and disclosures by report/update date; realtime snapshots by vendor cadence.
- Store historical bars separately from the latest snapshot. Record source time, fetch time, adjustment method, and missing fields.
- Store an immutable raw response and response hash, then derive normalized tables. Monitor API schema and vendor upgrade-log changes with fixed regression samples.
- Treat HTTP `401` as daily-quota exhaustion, `402` as an invalid token, `404` as a path/resource error, and `429` as rate limiting. Retry only `429`, network timeouts, and 5xx responses with bounded backoff; never log the token-bearing URL.
- Cite Zhitu for market data and the original exchange/company/government source for business, filing, policy, order, and capacity claims.

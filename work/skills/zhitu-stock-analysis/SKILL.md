---
name: zhitu-stock-analysis
description: Analyze or screen one or more eligible Shanghai/Shenzhen main-board A-shares with Zhitu Data Service APIs, primary disclosures, and global-market context. Use for realtime snapshots, batch candidate screening, limit-up opportunity research, review, fundamentals, industry position, evidence quality, overseas risk transmission, and transparent risk scoring with a user-provided Zhitu API token. Excludes ChiNext, STAR Market, ST/*ST, and other stocks outside the user's tradable main-board universe by default.
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
4. [references/global-risk-overlay.md](references/global-risk-overlay.md) when assessing the market, sector, event, next-session, or swing outlook.

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
5. **Build market context.** Read indices, breadth, limit-up/down/broken-board pools, sector concentration, liquidity, and the current market regime.
6. **Add the global overlay.** Assess US, Japanese, Korean, Hong Kong, commodity, FX, rate, overseas-policy, and geopolitical transmission using [references/global-risk-overlay.md](references/global-risk-overlay.md). Timestamp every observation.
7. **Create a data-only pre-screen.** Use liquidity, relative strength, turnover, trend, limit-up structure, sector breadth, and risk flags only to narrow research candidates. Label it `pre-screen`, not a final recommendation.
8. **Verify the business case.** For every surviving candidate, inspect filings, financial statements, official website disclosures, and investor-relations/research records. Quantify industry position, catalyst-related revenue share, earnings elasticity, validated orders, and validated capacity.
9. **Apply evidence gates and score caps.** Missing primary evidence must reduce the score. Theme heat cannot compensate for missing fundamentals or unverified commercial claims.
10. **Challenge the thesis.** State the strongest bearish explanation, invalidation conditions, crowded-trade risk, event expectations already priced in, and data gaps.
11. **Return timestamped output.** Separate facts, calculations, inferences, and unknowns. Show data-quality score before the stock score and cite primary evidence close to each material claim.

## Analysis modes

### Single stock

Return:

1. eligibility result;
2. data cutoff, quality score, quality flags, sources, and adjustment method;
3. price/liquidity snapshot and source/fetch timestamps;
4. market, sector, and global-risk regime;
5. fundamentals and industry position;
6. revenue exposure, earnings elasticity, order validation, and capacity validation;
7. evidence coverage table;
8. technical/flow observations;
9. bullish case, bearish case, invalidation conditions, and missing evidence;
10. transparent component scores, caps applied, and final research tier.

### Batch screen

Use two stages:

1. `Market-data pre-screen`: eligible universe, liquidity, relative strength, sector breadth, limit-up/down structure, and abnormal-risk filters.
2. `Research validation`: primary-source evidence and fundamental scoring for the smaller survivor set.

Show excluded symbols separately with reasons. Never publish a high-conviction list based only on price/volume or theme heat. If the batch is too large for primary-source verification, return a shortlist and mark every unverified name `pending research validation`.

### Review / 复盘

For daily review, compare the prior thesis with the close:

- which sectors supplied limit-ups, down-limits, and broken boards;
- whether breadth expanded or narrowed and whether leaders were one-day rotations or showed multi-day confirmation;
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

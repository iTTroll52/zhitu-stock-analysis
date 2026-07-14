---
name: zhitu-stock-analysis
description: Analyze eligible Shanghai/Shenzhen main-board A-shares for short-term research using Zhitu APIs, deterministic market-regime and participate/wait/cash states, sector rotation, bottom-launch/acceleration/limit structures, primary evidence, global context, event and attention-price divergence, shadow validation, conditional model exposure, and HTML reports. Use for single-stock or batch screening, intraday/next-session/2-5-session outlooks, market or sector review, empty-position decisions, catalyst/priced-in/negative-landing analysis, rotation candidates, signal-lifetime review, entry/invalidation conditions, and shareable reports. Defaults to excluding ChiNext, STAR, BSE, and ST/*ST. Does not provide long-term picks, target prices, guaranteed returns, or unvalidated probabilities.
---

# 智兔股票分析

Use Zhitu for structured market data and use primary sources for claims that Zhitu cannot prove. Treat every ranking as a research-priority model, never as a promise of profit or a personalized trade instruction.

Never expose a token in browser code, commands shown to the user, logs, generated files, or the final response. Read it from the server-side environment variable `ZHITU_API_TOKEN`.

For a safe entitlement smoke test, run `python scripts/test_connection.py`. The script reads only `ZHITU_API_TOKEN`, tests four low-frequency read-only endpoint families, and prints counts/status without response contents or the token.

Run `python scripts/self_check.py` after installation. Run `python scripts/data_quality.py <kind> <json-file>` to validate saved `quote`, `stock-list`, `bars`, `limit-pool`, or `financial-ratios` payloads before using them in analysis.

## Required references

Read these files before acting:

1. [references/zhitu-api.md](references/zhitu-api.md) for endpoint selection, cadence, and limitations.
2. [references/analysis-framework.md](references/analysis-framework.md) for scoring, evidence gates, and outputs.
3. [references/data-quality-gates.md](references/data-quality-gates.md) before accepting API, financial, historical, or backtest data.
4. [references/global-risk-overlay.md](references/global-risk-overlay.md) for every analysis; keep it focused on the requested short-term transmission window and never omit the data cutoff or overseas session state.
5. [references/sector-rotation.md](references/sector-rotation.md) for every single-stock analysis, batch screen, market review, or short-horizon outlook.
6. [references/rotation-candidates-and-positioning.md](references/rotation-candidates-and-positioning.md) whenever the user requests stocks corresponding to a rotation, entry conditions, position size, an aggressive/balanced/conservative plan, or a trade-oriented shortlist.
7. [references/automation.md](references/automation.md) before running the API client, deterministic pre-screen, rotation classifier, or T+1/T+5/T+20 evaluation ledger.
8. [references/short-term-selection.md](references/short-term-selection.md) before every screen, candidate list, position plan, or daily review.
9. [references/launch-and-limit-signals.md](references/launch-and-limit-signals.md) whenever the user requests bottom-launch, acceleration, likely limit-up, first-board, or consecutive-board candidates.
10. [references/html-report.md](references/html-report.md) whenever the user requests a browser-viewable, offline, printable, or shareable report.
11. [references/market-regime-and-cash.md](references/market-regime-and-cash.md) before every stock analysis, batch screen, market review, candidate list, or exposure plan.
12. [references/attention-and-event-reaction.md](references/attention-and-event-reaction.md) whenever news, announcements, topic heat, sentiment, priced-in positives, negative-news landing, or one-day themes are involved.
13. [references/rule-validation-and-shadow.md](references/rule-validation-and-shadow.md) before publishing any signal rank, claimed edge, strategy result, or model-exposure plan.

## Hard tradability gate

Apply this gate before fetching expensive data or ranking candidates:

- Default eligible universe: Shanghai and Shenzhen **main-board A-shares only**.
- Allow common Shanghai main-board prefixes `600`, `601`, `603`, `605` and Shenzhen main-board prefixes `000`, `001`, `002`, `003`, subject to instrument metadata confirmation.
- Exclude ChiNext prefixes `300` and `301`.
- Exclude STAR Market prefixes `688` and `689`.
- Exclude every name or code returned by the current ST list, including `ST`, `*ST`, delisting-risk, or equivalent special-treatment labels.
- Exclude BSE and any instrument outside the confirmed Shanghai/Shenzhen main-board universe unless the user explicitly changes the universe and confirms trading permission.

An excluded stock receives no opportunity score. Return the exact exclusion reason. Never allow technical strength, theme heat, or a limit-up record to override this gate.

## Hard truthfulness gate

Treat every user-facing analysis, score, ranking, candidate list, model-exposure plan, review statistic, backtest result, and shareable report as `production` analysis unless the user explicitly requests a software demonstration or test.

- Use only real API responses, real stored market records, and verifiable primary-source disclosures in production analysis.
- Never use fabricated, simulated, synthetic, mock, demo, test, placeholder, randomly generated, manually invented, or model-generated market/fundamental values in production analysis.
- Never mix demo/test data with real data. Never use demo/test output in screening, ranking, exposure, signal tracking, backtests, calibration, hit-rate statistics, or performance claims.
- Never infer a missing numeric value merely to complete a table or report. Preserve the field as unknown with its missing reason.
- If required real data is unavailable, stale, permission-denied, conflicting, or below the quality threshold, return `insufficient real data`; do not produce a candidate score, rank, probability, or exposure plan.
- Allow demo/test data only when `analysis_mode` is explicitly `demo` or `test`. Mark every resulting artifact conspicuously as non-real and not for trading.
- Before producing HTML, require the production payload to pass the same truthfulness, timestamp, quality, source, and tradability gates as the written analysis. Do not turn unverified text into an authoritative-looking report.

## Inputs

Accept:

- one stock code for a full diagnostic;
- several codes for comparison;
- a market-wide or sector screen;
- a requested horizon: intraday observation, next session, 2–5 sessions, or a secondary 5–20-session continuation check.

Default to short-term research. Do not produce long-term picks, long-term target prices, or long-term holding plans. Keep fundamentals, orders, capacity, and industry position as catalyst-verification and risk filters for short-term or medium-term continuation.

Normalize symbols and confirm board/type with instrument metadata where possible. Split realtime multi-symbol requests into batches of at most 20. If no token is available, produce the request plan and evidence checklist without inventing live values.

## Workflow

1. **Set the short-term target.** Define one outcome and cutoff. Keep `next-session limit-up`, `next-session positive return`, and `five-session excess return` as separate labels. Use 5–20 sessions only for secondary continuation review.
2. **Apply the tradability gate.** Remove ineligible boards and ST/*ST before ranking.
3. **Apply the data-quality gate.** Validate shape, fields, units, freshness, formulas, missing-value reasons, adjustment method, and point-in-time availability using [references/data-quality-gates.md](references/data-quality-gates.md). Stop scoring on hard errors or a score below 80.
4. **Reconcile material data.** Compare realtime endpoint families within the same source-time window. Verify key financial values with an independent source and use the original filing to resolve differences above 5%.
5. **Build the mandatory market and rotation pack.** For every analysis, report core-index direction, multi-period trend, total-market liquidity versus comparable windows, breadth, limit-up/down/broken-board structure, style, current market regime, and sector concentration. Run `scripts/market_regime.py` on a time-aligned normalized market pack and return `participate / wait / cash` plus support, counter-evidence, release conditions, and validation status. Classify sectors by rotation stage using [references/sector-rotation.md](references/sector-rotation.md); report which sectors are leading, strengthening, diverging, fading, or only candidates for observation.
6. **Add the mandatory global overlay.** For every analysis, assess US, Japanese, Korean, Hong Kong, commodity, FX, rate, overseas-policy, and geopolitical transmission using [references/global-risk-overlay.md](references/global-risk-overlay.md). Timestamp every observation and identify whether each market is intraday, closed, or from the prior session.
7. **Create a data-only pre-screen.** Use liquidity, relative strength, turnover, trend, limit-up structure, sector breadth, and risk flags only to narrow research candidates. Label it `pre-screen`, not a final recommendation. For launch/acceleration/limit-up requests, run `scripts/short_term_signals.py` and preserve its separate signal labels.
8. **Verify the business case.** For every surviving candidate, inspect filings, financial statements, official website disclosures, and investor-relations/research records. Quantify industry position, catalyst-related revenue share, earnings elasticity, validated orders, and validated capacity.
9. **Evaluate real events and attention only when available.** Separate attention, credibility, market confirmation, and crowding. Deduplicate reposts, compare the event with pre-event price action and post-release 5/15/30-minute behavior, and classify priced-in positives or negative-news landing using [references/attention-and-event-reaction.md](references/attention-and-event-reaction.md). If real event/attention observations are unavailable, return `not_available`; never let the model invent them.
10. **Declare the rule status.** Mark every signal/ruleset `experimental`, `shadow`, `validated`, or `suspended` using [references/rule-validation-and-shadow.md](references/rule-validation-and-shadow.md). Missing validation defaults to `experimental`. Keep objectives and ruleset versions separate.
11. **Build conditional candidates and exposure.** When requested, map confirmed rotation stages to eligible main-board candidates and produce a model-portfolio research-exposure plan using [references/rotation-candidates-and-positioning.md](references/rotation-candidates-and-positioning.md). Separate `initial`, `confirmation`, and `maximum` exposure; include entry, no-chase, reduction, invalidation, and cash conditions. If the rule is not validated, label the range heuristic/experimental and never claim a demonstrated edge.
12. **Apply evidence gates and score caps.** Missing primary evidence must reduce the score. Theme or social heat cannot compensate for missing fundamentals or unverified commercial claims.
13. **Challenge the thesis.** State the strongest bearish explanation, invalidation conditions, crowded-trade risk, event expectations already priced in, and data gaps.
14. **Return timestamped output.** Separate facts, calculations, inferences, and unknowns. Show data-quality score and strategy-validation status before the stock score and cite primary evidence close to each material claim.
15. **Stay short-term focused.** Return at most 3 priority candidates and 5 watch candidates. Do not append a long-term list. Return no candidates when the market, data, evidence, or validation gate requires waiting/cash.
16. **Render HTML when requested.** Save the normalized, timestamped production analysis as JSON with `analysis_mode: production` and run `python scripts/generate_html_report.py analysis.json --output report.html`. Keep the HTML self-contained and remove tokens, restricted raw payloads, and personal information before sharing. Use `--allow-demo` only for an explicitly labeled software demonstration or test artifact.

For reproducible execution, use `scripts/zhitu_client.py` for API access, `scripts/screen_main_board.py` for the market-data pre-screen, `scripts/market_regime.py` for market state and participate/wait/cash posture, `scripts/sector_rotation.py` for point-in-time rotation stages, `scripts/short_term_signals.py` for launch/acceleration/limit structures, `scripts/evidence_gate.py` for primary-evidence caps, `scripts/research_tracker.py` for version-separated outcome tracking, and `scripts/generate_html_report.py` for portable browser reports. Do not replace their deterministic outputs with silently changed thresholds.

## Analysis modes

### Single stock

Return:

1. eligibility result;
2. data cutoff, quality score, quality flags, sources, and adjustment method;
3. price/liquidity snapshot and source/fetch timestamps;
4. mandatory market/global dashboard: core indices, liquidity, breadth, style, overseas session state, rates/FX/commodities, transmission to A shares, market regime, and `participate/wait/cash` posture;
5. sector-rotation position: the target sector's stage, current leaders, strengthening sectors, fading sectors, and evidence against the classification;
6. fundamentals and industry position;
7. revenue exposure, earnings elasticity, order validation, and capacity validation;
8. evidence coverage table;
9. technical/flow observations;
10. event/attention-price divergence when real observations exist, otherwise `not_available`;
11. bullish case, bearish case, invalidation conditions, cash/release conditions, and missing evidence;
12. strategy-validation status, transparent component scores, caps applied, and final research tier.

### Batch screen

Use two stages:

1. `Market-data pre-screen`: eligible universe, liquidity, relative strength, sector breadth, limit-up/down structure, and abnormal-risk filters.
2. `Research validation`: primary-source evidence and fundamental scoring for the smaller survivor set.

Before ranking stocks, show the mandatory market/global dashboard, `participate/wait/cash` posture, and a sector-rotation table with current leaders, newly strengthening groups, crowded/diverging groups, fading groups, and unconfirmed watch candidates. Show excluded symbols separately with reasons. Never publish a high-conviction list based only on price/volume or theme heat. If the market gate returns cash, output an empty priority list plus release conditions. If the batch is too large for primary-source verification, return a shortlist and mark every unverified name `pending research validation`.

Split output only into `short-term priority`, `short-term watch`, `secondary 5-20-session continuation`, and `excluded`. Never create a long-term candidate section.

Within the short-term output, keep `bottom_start`, `accelerating`, `limit_up`, and `consecutive_limit_up` separate. A stock may match several signals, but assign one primary label using the fixed precedence in [references/launch-and-limit-signals.md](references/launch-and-limit-signals.md).

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
- which signals remain `active`, became `aging`, were `invalidated`, `expired`, or caused the ruleset to be `suspended`;
- whether score thresholds or features need backtest review, without changing rules merely to fit one day.

## Integrity rules

- Do not call vendor dynamic PE `TTM` unless independently confirmed.
- Do not infer causation from co-movement with an overseas index.
- Do not treat capital flow, chip distribution, five-level quotes, limit-up pools, or technical indicators as proof of future returns or complete Level-2 data.
- Do not present inferred `main-force` intent as fact. Use observable capital-behavior language and provide a competing explanation.
- Do not describe planned capacity as commissioned capacity, a framework agreement as an order, an order as recognized revenue, or an industry TAM as company revenue exposure.
- Avoid look-ahead bias. Use only evidence available before the prediction cutoff.
- Never convert missing, permission-denied, stale, or API-error fields to zero. Keep the reason code and lower data quality.
- Preserve period end, first disclosure, revision, fetch, and model-availability times. Do not overwrite historical values with later restatements.
- Do not use a payload that fails deterministic formula/schema checks. Do not average conflicting snapshots before comparing source timestamps.
- Do not claim `high probability` until a fixed rule has out-of-sample results with sample size, base rate, cutoff time, costs, limit-up fill assumptions, and confidence interval. Otherwise use `higher research priority` or `signal score`.
- Do not call a ruleset validated merely because it reached a minimum sample count. Require a time-separated out-of-sample record and keep each objective/ruleset version separate.
- Do not use news count, repost count, keyword frequency, model sentiment, or topic heat as proof of company benefit or future direction. Separate attention from credibility, price confirmation, and crowding.

## Operations

- The all-market realtime endpoint is eligible-plan dependent, updates about once per minute, and should not be requested more than once per minute.
- Cache universe/ST lists daily; financials, profiles, holders, and disclosures by report/update date; realtime snapshots by vendor cadence.
- Store historical bars separately from the latest snapshot. Record source time, fetch time, adjustment method, and missing fields.
- Store an immutable raw response and response hash, then derive normalized tables. Monitor API schema and vendor upgrade-log changes with fixed regression samples.
- Set `ZHITU_REQUESTS_PER_MINUTE` to the purchased plan ceiling or lower. The client defaults to 1000 and respects endpoint-specific cache cadence; do not use parallel processes to bypass the vendor limit.
- Treat `scripts/screen_main_board.py` as a market-data pre-screen only. Complete primary-source fundamental validation before promoting any candidate to a research tier or model-position plan.
- Record every time-bound signal before its outcome exists, including cutoff, price, objective, benchmark, ruleset version, and evidence gaps. Evaluate T+1/T+5/T+20 only from later stored sessions.
- Run `scripts/market_regime.py` before candidate construction. A blocked/unknown market state cannot produce a formal candidate or exposure plan; a cash state must include explicit release conditions.
- Use `scripts/research_tracker.py ... report --min-sample N` only as a descriptive validation report. Never merge different `ruleset_version` values or treat `minimum_reached` as proof of sample-out validation.
- Default candidate selection and position planning to T+1 and T+5. Use T+20 only to evaluate secondary continuation, never to create a long-term recommendation.
- Treat HTTP `401` as daily-quota exhaustion, `402` as an invalid token, `404` as a path/resource error, and `429` as rate limiting. Retry only `429`, network timeouts, and 5xx responses with bounded backoff; never log the token-bearing URL.
- Cite Zhitu for market data and the original exchange/company/government source for business, filing, policy, order, and capacity claims.

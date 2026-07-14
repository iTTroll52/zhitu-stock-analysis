# 轮动候选与仓位规划

Use this reference only after the tradability, data-quality, market/global, sector-rotation, and primary-evidence gates. Return conditional research candidates and a model-portfolio exposure plan, not guaranteed picks or individualized execution orders.

## 1. Candidate construction

For every material rotation bucket, consider at most two candidates per sector and identify the role:

- `leader`: strongest verified leadership and breadth contribution;
- `bellwether`: liquid sector representative suitable for confirmation;
- `fundamental confirmation`: filing-supported earnings, order, price, capacity, or margin evidence;
- `adjacent-chain candidate`: upstream/downstream exposure with company-level evidence;
- `trade-only satellite`: strong market signal but incomplete fundamental evidence; keep exposure lower.

Exclude a candidate when:

- it fails the main-board or current ST/*ST gate;
- current data quality is below 80 or a hard error remains;
- its only support is a concept tag, rumor, capital-flow label, or one-day price move;
- a core order, capacity, revenue-share, or earnings claim lacks primary evidence;
- liquidity, suspension, limit-up availability, or exit constraints make the stated position unrealistic.

If live quotes, the current ST list, or comparable intraday windows are unavailable, label the output `conditional watchlist`, omit precise entry prices, and cap the proposed aggregate exposure at the lower end of the applicable regime range.

## 2. Required output table

| Priority | Code/name | Board/ST result | Sector/role | Rotation stage | Primary reasons | Counter-evidence | Initial % | Confirmation % | Maximum % | Entry condition | Invalidation |
|---|---|---|---|---|---|---|---:|---:|---:|---|---|

Keep stock, sector, and portfolio percentages distinct. Do not imply that all listed candidates should be bought together; mark mutually substitutable candidates in the same sector.

## 3. Portfolio exposure ranges

Use these as default model-portfolio ranges before the user's personal constraints are known:

| Market/rotation regime | Aggregate equity exposure | Interpretation |
|---|---:|---|
| `high uncertainty` or broad `fading` | 0%–25% | Observation or small probes only |
| broad rebound or early `starting` | 25%–40% | Staged participation; confirmation still missing |
| broad `strengthening` with breadth and liquidity confirmation | 40%–60% | Balanced-aggressive participation |
| `accelerating` but crowded/diverging | 35%–55% | Keep exposure meaningful but reserve capacity for volatility |
| strong multi-session trend with out-of-sample-confirmed rules | 50%–70% | Use only when the evidence and historical validation support it |

Default concentration limits unless the user supplies a tested mandate:

- one stock: 15% maximum;
- one sector: 25% maximum;
- correlated sectors/themes combined: 35% maximum;
- trade-only satellite: 8% initial and 10% maximum;
- no leverage or borrowed funds.

Do not mechanically choose the top of a range. Move upward only when market breadth, comparable-window liquidity, sector persistence, stock availability, and primary evidence confirm together.

## 4. Staged entry

Default to three tranches of the candidate's target exposure:

1. `50%` after the market and sector confirm rather than at an unverified opening print;
2. `30%` after a pullback or consolidation holds without breadth deterioration;
3. `20%` after later-session or closing confirmation.

For a stock that was limit-up, rose sharply, or gaps materially on new information:

- do not chase the full target at the open;
- compare the gap with the event's verified earnings or business impact and with sector breadth;
- reduce or skip the first tranche when the stock opens materially above the prior close and cannot hold the opening range;
- never assume a limit-up order can be filled.

Percentage gap thresholds are heuristics until backtested. Label them as execution guards, not predictive facts.

## 5. Confirmation and invalidation

Require explicit conditions for adding exposure, such as:

- market breadth remains positive and does not rapidly reverse;
- total-market and sector turnover stay healthy versus the same clock-time comparison;
- sector median performance, leaders, and liquid bellwethers confirm together;
- the candidate remains available and does not show a high-open/low-close failure;
- new filings or official events strengthen rather than contradict the thesis.

Define reduction or exit-review conditions before presenting the position:

- sector changes from `strengthening` to `diverging/fading`;
- leadership narrows while broken-board or downside participation rises;
- the candidate loses the relevant event-day or confirmation structure on expanding volume;
- the filing, order, price, capacity, or overseas transmission assumption is invalidated;
- market/global risk moves outside the scenario used to size exposure.

State whether invalidation is intraday observation, closing confirmation, or a multi-session rule. Do not silently change it after the outcome.

## 6. Position explanation

Explain every proposed percentage through four components:

1. market/global risk budget;
2. sector stage and breadth;
3. company evidence quality and earnings/business elasticity;
4. crowding, liquidity, gap, and exit risk.

When the user requests a less conservative plan, use the balanced-aggressive range only if the gates support it. Increasing risk tolerance does not override ST/board exclusions, missing evidence, failed data quality, sector divergence, concentration limits, or execution constraints.

## 7. Review and calibration

Persist the recommendation cutoff, candidate set, proposed ranges, triggers, actual availability, and later outcomes. Review at T+1 and T+5:

- whether entry conditions were actually available;
- sector and stock excess returns;
- maximum favorable/adverse excursion;
- whether the proposed initial and maximum exposure were appropriate;
- false positives by rotation stage and evidence tier.

Only tighten or expand exposure ranges after time-separated, out-of-sample validation with costs and limit-up/limit-down execution assumptions.

# 板块轮动定位

Use this module in every single-stock analysis, batch screen, and daily review. It identifies where market attention and participation are moving; it does not assert that a sector must rise next.

## 1. Classification unit

- Separate primary industries from concepts. Do not mix them in one ranking.
- Deduplicate stocks that belong to several concepts so one active stock does not create several false sector signals.
- Use a fixed constituent snapshot for each calculation window and record its effective date.
- Keep the target stock's industry, concepts, upstream/downstream links, and benchmark index distinct.

## 2. Required observation windows

Compare at least the current session, 3 sessions, 5 sessions, and 20 sessions. For intraday work, compare the current observation with the same clock time on prior sessions when available; do not compare morning turnover directly with a previous full-day total.

For each sector record:

| Dimension | Required evidence |
|---|---|
| Relative performance | Sector return versus the broad-market and appropriate style benchmark |
| Participation | Advancers, decliners, median return, share above key moving averages |
| Liquidity | Turnover value, share of total-market turnover, and change versus comparable windows |
| Limit structure | First-board, multi-board, limit-up, limit-down, broken-board counts and rate |
| Leadership | Leader, liquid bellwether, follower breadth, and leader/breadth divergence |
| Persistence | 3/5/20-session relative strength and next-session follow-through |
| Catalyst evidence | New filing, policy, order, price, capacity, or earnings evidence and whether it is already priced |
| External mapping | Overseas peer, commodity, FX, rate, policy, or geopolitical support and its timestamp |

## 3. Rotation stages

Assign one stage and a confidence level to every material sector:

| Stage | Typical evidence | Interpretation |
|---|---|---|
| `dormant` | Weak relative strength, low participation, no liquidity expansion | No verified rotation signal |
| `starting` | Relative strength and comparable-window turnover begin to improve from a low base; participation broadens | Early observation candidate, not confirmation |
| `strengthening` | Multi-session excess return, expanding breadth, rising turnover share, leaders and bellwethers align | Rotation is being confirmed |
| `accelerating` | Strong breadth, limit-up expansion, high turnover and multiple leaders | Strong but crowding risk is rising |
| `diverging` | Index/leader stays strong while median stock, breadth, or follow-through weakens; broken boards rise | Late-stage disagreement; avoid calling it healthy acceleration |
| `fading` | Relative strength, breadth, turnover share, and leader continuity deteriorate | Capital attention is leaving or pausing |
| `rebounding` | A faded sector improves again with renewed breadth and evidence | Treat separately from a first-time start |

Never infer a stage from one indicator. Require confirmation from at least three independent groups: price/relative strength, participation/breadth, liquidity/turnover, limit structure/leadership, or primary catalyst evidence.

## 4. Mandatory output

Every analysis must include a compact rotation table:

| Bucket | Sector | Stage | Evidence | Counter-evidence | Confidence |
|---|---|---|---|---|---|
| Current leader |  |  |  |  |  |
| Newly strengthening |  |  |  |  |  |
| Crowded/diverging |  |  |  |  |  |
| Fading |  |  |  |  |  |
| Watch candidate |  |  |  |  |  |

Then state:

1. where the target stock's sector sits in the sequence;
2. whether the target is a leader, liquid bellwether, follower, or unrelated concept tag;
3. which adjacent upstream/downstream sectors are receiving confirmation;
4. what evidence would advance or downgrade the stage;
5. the observation cutoff and next planned refresh.

Use `watch candidate` instead of `next sector` when evidence is incomplete. Do not say capital will rotate to a sector merely because it is low, has not risen, or resembles a previous cycle.

## 5. Accuracy and failure controls

- A high sector average driven by one or two stocks is not broad rotation; report the median and participation distribution.
- Do not treat a concept-tag count as capital flow. Verify turnover share and constituent-level breadth.
- Use float-adjusted or capped weighting where possible so mega-caps do not dominate; show equal-weight results for breadth.
- Distinguish volume transferred from another sector from market-wide liquidity expansion.
- Align Zhitu realtime data to its vendor timestamp. Limit-up pool data may update more slowly than quotes; display both timestamps.
- Mark a sector `unconfirmed` when constituent membership, historical coverage, or comparable-window data is incomplete.
- Evaluate stage transitions out of sample. Report base rates, next-session/5-session excess returns, drawdowns, costs, and confidence intervals before treating stages as predictive.

## 6. Daily review

Persist the prior day's stage label and evidence snapshot. At the close, record:

- confirmed transition, unchanged, false start, failed acceleration, or rebound failure;
- next-session sector excess return and breadth change;
- whether leadership broadened or narrowed;
- whether a catalyst gained primary evidence or was merely repeated;
- which threshold generated false positives.

Do not rewrite the prior label after seeing the outcome. Adjust a rule only after a sufficiently large, time-separated validation sample.

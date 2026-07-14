# 智兔 API 速查

Source documents:

- https://www.zhituapi.com/hsstockapi.html
- https://www.zhituapi.com/hsindexapi.html
- https://www.zhituapi.com/bjdataapi.html

## API domains

| Domain | Use | Core endpoints / data |
|---|---|---|
| Universe | Resolve names and market | `/hs/list/all`, `/hs/list/fx`, instrument metadata and new-share list. Default workflow does not use `/bj/list/all` because BSE is outside the configured tradable universe. |
| Realtime | Current snapshot | `/hs/public/realall` for all eligible A shares; `/hs/public/ssjymore` for up to 20; single-stock realtime endpoints; index realtime `/hz/real/ssjy/{code}` |
| History | Price/volume calculations | Latest/history bars for 5/15/30/60-minute, day/week/month/year and specified adjustment method |
| Technical | Descriptive indicators | MA, MACD, KDJ history |
| Fundamentals | Quality and valuation analysis | Three financial statements, financial ratios, company overview, dividends |
| Ownership | Governance and supply/demand context | Top holders, shareholder-count trend, executive history |
| Market context | Breadth and themes | Concept/primary-sector lists and members, limit-up pools, index data |

## Known cadence and plan caveats

- Stock lists and ST data: daily.
- New-share calendar: daily after market.
- Limit-up pool: every 10 minutes during trading.
- All-market and up-to-20-stock public realtime interfaces: one-minute update cadence. All-market has one-request-per-minute limit and eligible-plan restriction.
- Financial, shareholder, executive, and dividend data are not realtime; treat their disclosed report date as essential metadata.
- Rate limits vary by plan. Use the provider's current document and contract as the source of truth.
- Monitor the provider upgrade log before releases. Endpoint availability, fields, and minute-adjustment rules can change; run fixed payload regression tests after a documented change.

## Error semantics

| HTTP status | Meaning | Client action |
|---|---|---|
| `401` | Daily request allowance exhausted | Stop non-critical calls; do not retry until allowance resets. |
| `402` | Invalid/nonexistent token | Stop and request credential correction. |
| `404` | Resource or URL not found | Validate endpoint, code, date, and API version. |
| `429` | Per-minute rate exceeded | Retry with exponential backoff and jitter. |

Network timeouts and 5xx errors may be retried 2–3 times. Never record the full token-bearing URL in logs.

## Code and batching

- Many沪深 endpoints take six-digit codes, while historical/indicator endpoints may require code plus market suffix, e.g. `000001.SZ`.
- The configured default universe is Shanghai/Shenzhen main board only. Reject ChiNext `300/301`, STAR `688/689`, BSE, and current ST/*ST names before analysis.
- Batch the multi-select realtime endpoint in groups of 20; deduplicate codes before calling.

## Endpoint routing for this skill

| Task | Preferred endpoint family | Notes |
|---|---|---|
| Tradable-universe gate | `/hs/list/all`, `/hs/list/fx`, `/hs/instrument/{code}` | Refresh lists daily and confirm board/type before ranking. |
| Single snapshot | `/hs/real/ssjy/{code}` or `/hs/real/time/{code}` | Preserve returned timestamp; entitlement may differ. |
| Up to 20 snapshots | `/hs/public/ssjymore` | Split and deduplicate batches. |
| All-market pre-screen | `/hs/public/realall` | Eligible plan only; no more than once per minute. |
| Five-level quote | `/hs/real/five/{code}` | Snapshot/depth aid, not complete exchange L2. |
| Limit-up/down/broken-board review | `/hs/pool/ztgc/{date}`, `/hs/pool/dtgc/{date}`, `/hs/pool/zbgc/{date}` | Use sector, seal/break, and continuity fields as descriptive signals. |
| Bars | `/hs/latest/{code}/{freq}/{adjust}`, `/hs/history/{code}/{freq}/{adjust}` | Record frequency and adjustment. |
| Technical indicators | `/hs/history/{macd,ma,boll,kdj}/{code}/{freq}/{adjust}` | Descriptive only. |
| Daily indicators/valuation | `/hs/indicators/{code}` | Confirm field definitions and date. |
| Financial statements | `/hs/fin/{balance,income,cashflow,ratios}/{code}` | Preserve period and disclosure metadata. |
| Ownership/capital | `/hs/fin/{capital,topholder,flowholder,hm}/{code}` | Do not infer investor intent from changes alone. |

## Do not claim from this API alone

- Complete exchange-authorized Level-2 depth, full order queue, or legally redistributable L2 data.
- News interpretation, complete announcement text, research-report text, or brokerage execution.
- Overseas indices, official foreign policy/geopolitical documents, company announcement text, industry market share, order authenticity, capacity commissioning, or catalyst-related revenue share unless the endpoint explicitly returns primary evidence.
- A causal relationship or future return based only on price, technical, capital-flow, or limit-up fields.

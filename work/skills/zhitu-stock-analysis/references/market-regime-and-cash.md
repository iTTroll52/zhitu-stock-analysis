# 市场状态、参与与空仓

在任何个股排名、轮动候选或模型仓位之前先判断市场。空仓、等待和不产生候选都是正式有效结果。

## 必需输入

使用同一预测截点的真实数据：

- 核心指数涨跌和趋势；
- 上涨/下跌家数、全市场中位数、20日均线上方比例；
- 总成交额相对历日同一时刻的比例；
- 涨停、跌停、炸板和连板结构；
- 强化、加速、分化和退潮板块数量；
- 数据质量、`source_time` 和 `cutoff_time`。

缺少四类独立市场指标、数据质量低于80、关键行情过期或时间未对齐时，输出 `insufficient_data`，不得用指数涨跌单独替代市场状态。

## 执行

将标准化聚合保存为 JSON 后运行：

```powershell
python scripts/market_regime.py market.json --output market-regime.json
```

脚本输出：

- `regime`：`broad_bull / structural_bull / range / transition / structural_bear / broad_bear / crisis`；
- `posture`：`participate / selective_participation / wait_or_selective / wait / cash_preferred / cash`；
- `research_exposure_band`：研究组合范围，不是个性化仓位指令；
- 五类确定性组件、支持理由、反证、验证状态和阻断原因。

脚本阈值是透明初始规则。没有样本外验证时 `publication_status` 必须为 `experimental_research_state`，不得称为已验证择时模型。

## 输出要求

每次分析先展示：

1. 数据截点和质量；
2. 市场状态及五类组件；
3. `参与 / 等待 / 空仓`；
4. 支持证据和最强反证；
5. 空仓/等待开始条件、解除条件和失效条件；
6. 策略验证状态。

结构牛只允许聚焦已确认主线，不能因指数上涨扩大到全市场。`transition`、熊市或危机状态下，没有合格候选是正常输出，禁止为了每天推荐而降低门槛。

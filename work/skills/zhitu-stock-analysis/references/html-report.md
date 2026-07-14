# HTML 分析报告

当用户需要浏览器展示、离线查看、打印 PDF 或分享分析结果时，生成自包含 HTML 报告。

## 执行

先完成主板过滤、数据质量、大盘/海外、板块轮动、短线信号、证据闸门与正反逻辑，再把规范化结果保存为 JSON：

```powershell
python scripts/generate_html_report.py analysis.json --output report.html
```

生成文件不引用 CDN、外部字体、图片或脚本，可直接双击打开。报告支持明暗模式、候选信号过滤、打印和浏览器「另存为 PDF」。

正式分析默认使用 `analysis_mode: production`。严禁用演示、模拟、测试、占位或模型编造数据生成正式候选、评分和仓位报告。演示文件必须显式写入 `analysis_mode: demo`，并使用：

```powershell
python scripts/generate_html_report.py demo.json --output demo.html --allow-demo
```

生产模式包含候选时，生成器必须同时确认：数据质量分不低于 80、存在明确数据截止时间、候选代码为真实六位沪深代码、至少存在一个有效 HTTP(S) 来源，并且负载中没有演示/模拟标记。任一条件失败即拒绝生成。

## 输入结构

JSON 根节点必须是对象。字段允许缺失；缺失内容会明确显示「未提供」，不会补造数据。缺失真实数据时不得为了完整展示而产生候选、评分或仓位。

| 字段 | 类型 | 说明 |
|---|---|---|
| `analysis_mode` | string | 正式分析固定为 `production`；仅软件演示可用 `demo` 或 `test` |
| `title` / `subtitle` | string | 报告标题与副标题 |
| `generated_at` | string | 报告生成时间，含时区 |
| `data_cutoff` | string | 分析证据截点，含时区 |
| `market_session` | string | 盘前、盘中、收盘后或海外上一交易日 |
| `data_quality` | object | `score`、`status`、`flags[]` |
| `summary` | object | `verdict`、`confidence`、`key_reason`、`tier` |
| `market[]` / `global[]` | array | `name`、`value`、`change_pct`、`session` |
| `market_regime` | object | `regime`、`posture`、`research_exposure_band`、组件、理由、反证和解除条件 |
| `rotation` | object | `stage`、`current`、`narrative`、`leaders[]`、`strengthening[]`、`fading[]` |
| `signals[]` | array | `key`、`label`、`count`、`note` |
| `strategy_validation` | object | `status`、`objective`、`ruleset_version`、样本量和样本外状态 |
| `event_reaction` | object | 注意力、可信度、市场确认、拥挤度和事件分类；无真实数据时为 `not_available` |
| `candidates[]` | array | 代码、名称、板块、主信号、分数、理由、仓位及失效条件 |
| `evidence[]` | array | `category`、`status`、`summary`、`available_at` |
| `bull_case[]` / `bear_case[]` | array | 可验证的支持与反方逻辑 |
| `risks[]` | array | 不追、减仓或失效条件 |
| `sources[]` | array | `name`、`url`、`kind`、`published_at` |

候选的仓位结构：

```json
{
  "code": "600000",
  "name": "示例公司",
  "sector": "示例板块",
  "primary_signal": "bottom_start",
  "score": 72,
  "tier": "观察",
  "reasons": ["放量站回关键均线", "板块由启动转强化"],
  "exposure": {
    "initial": "5%-8%",
    "confirmation": "8%-12%",
    "maximum": "15%"
  },
  "no_chase": "高开超过 5% 不追",
  "invalidation": "跌破放量启动日低点"
}
```

`primary_signal` 固定使用 `bottom_start`、`accelerating`、`limit_up` 或 `consecutive_limit_up`。报告最多展示 3 个优先候选和 5 个观察候选，且不得绕过主板/ST、数据质量、市场状态、规则验证和一手证据闸门。市场状态为 `cash` 或分析被阻断时，优先候选必须为空并展示解除条件。

## 公开分享检查

生成前删除任何 Token、未授权原始响应、个人身份信息和付费数据的不可再分发字段。公开报告仅保留分析所需摘要、时间戳和允许公开的来源链接。HTML 文件中的仓位必须标为模型组合区间，不得写成个性化买卖指令。

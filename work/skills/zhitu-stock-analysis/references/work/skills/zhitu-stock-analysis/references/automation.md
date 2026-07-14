# 可执行分析与复盘

## 目录

1. 自检与配置
2. API 客户端
3. 主板预筛
4. 板块轮动
5. 信号复盘
6. 一手证据闸门
7. 准确性边界

## 1. 自检与配置

先运行：

```powershell
python scripts/self_check.py
python scripts/test_connection.py
```

只从服务器环境变量 `ZHITU_API_TOKEN` 或用户配置文件 `~/.config/zhitu-stock-analysis/.env` 读取 Token。可使用：

```dotenv
ZHITU_API_TOKEN=replace_me
ZHITU_REQUESTS_PER_MINUTE=1000
ZHITU_CACHE_DIR=D:\data\zhitu-cache
```

不要把用户配置文件复制进仓库。跨 CLI 使用时优先配置用户级环境变量，避免依赖当前工作目录。

## 2. API 客户端

`scripts/zhitu_client.py` 提供统一端点注册、分钟限速、有限重试、不可变原始响应、响应哈希和按接口更新频率缓存。

示例：

```powershell
python scripts/zhitu_client.py quote --path code=600000 --output quote.json
python scripts/zhitu_client.py limit_up --path date=2026-07-15 --output limit-up.json
python scripts/zhitu_client.py financial_ratios --path symbol=600000.SH --param st=20250101 --output ratios.json
```

命令行只输出端点名、血缘或保存后的内容，不输出 Token。`401/402/404` 不重试；`429/5xx/超时` 才执行有限退避。

## 3. 主板预筛

运行：

```powershell
python scripts/screen_main_board.py --codes 600000 000001 --top 20 --output screen.json
```

脚本执行以下硬规则：

- 先读取全市场和 ST 清单；
- 只允许沪深主板代码前缀，并再次检查名称及 ST 清单；
- 行情未通过确定性质量闸门时停止评分；
- 市场数据分由流动性、相对强弱、换手、日内强度、波动质量、估值字段和涨停结构组成；
- 输出必须标记 `pending primary-source research validation`。

该分数只用于缩小研究范围。不得与 100 分基本面研究分混用，也不得解释成上涨或涨停概率。

## 4. 板块轮动

`scripts/sector_rotation.py` 接受带历史时点的标准化股票快照：

```json
[
  {
    "date": "2026-07-15",
    "code": "600000",
    "sector": "银行",
    "change_pct": 1.2,
    "amount": 123456789,
    "limit_up": false,
    "broken_limit": false
  }
]
```

运行：

```powershell
python scripts/sector_rotation.py snapshots.json --output rotation.json
```

必须保证：

- 每天使用相同盘中截点或都使用收盘数据；
- 使用当时可得的板块成分，不能用今天的成分回填历史；
- `amount` 单位保持一致；
- 空行业映射不得自动归入“其他”；
- 阶段标签只是描述规则，必须同时输出指标和反证。

## 5. 信号复盘

初始化账本：

```powershell
python scripts/research_tracker.py --db research.sqlite3 init
```

记录预测截点时的信号：

```json
{
  "signals": [{
    "code": "600000",
    "signal_date": "2026-07-15",
    "cutoff_time": "2026-07-15T15:10:00+08:00",
    "signal_price": 10.0,
    "benchmark": "000300",
    "benchmark_price": 4000.0,
    "objective": "t1_positive",
    "score": 72,
    "ruleset_version": "2.0.0"
  }]
}
```

```powershell
python scripts/research_tracker.py --db research.sqlite3 record signals.json
```

逐交易日导入收盘快照；不要预先生成未来日期：

```json
{
  "snapshots": [{
    "trade_date": "2026-07-16",
    "code": "600000",
    "close": 10.2,
    "high": 10.3,
    "previous_close": 10.0,
    "limit_up_price": 11.0,
    "benchmark": "000300",
    "benchmark_close": 4020.0
  }]
}
```

```powershell
python scripts/research_tracker.py --db research.sqlite3 snapshot closes.json
python scripts/research_tracker.py --db research.sqlite3 evaluate
python scripts/research_tracker.py --db research.sqlite3 report
```

复盘按实际存在的后续交易日计算 T+1/T+5/T+20，输出样本量、命中率、平均收益、平均超额收益和 Wilson 95% 区间。

## 6. 一手证据闸门

市场预筛后，为每个候选建立证据 JSON，并执行：

```powershell
python scripts/evidence_gate.py evidence.json --output evidence-report.json
```

`evidence` 中每项必须包含 `category`、`source_url`、`available_at`、`strength` 和 `status`。类别仅允许 `filing`、`financial_report`、`official_company`、`investor_relations`、`industry_position`、`revenue_exposure`、`order`、`capacity`。同一类别只取最佳证据，不因重复转载累计加分。

脚本拒绝预测截点以后才公开的证据，自动执行缺失财报、公司一手资料、订单和产能的封顶规则。公司官网域名无法由通用脚本可靠识别时，必须人工确认域名归属。

## 7. 准确性边界

- 不足一个完整市场周期、样本量过小或没有样本外区间时，不把命中率外推为未来概率。
- 统计前固定 `objective`、截点、规则版本、买入可成交假设、手续费和滑点。
- `T+1 触及涨停` 必须同时提供盘中最高价和按交易所规则计算的精确涨停价；缺少任一字段时不记录该结果，禁止用收盘涨幅近似替代。
- 评分规则发生实质变化时提升 `ruleset_version`，不得把不同版本直接合并后宣称准确率提高。
- 新闻、公告、订单、产能和收入占比仍需一手来源采集与人工/模型核验，不能由行情 API 自动证明。

# Zhitu Stock Analysis Skill / 智兔股票分析 Skill

[中文](#中文说明) · [English](#english)

> An evidence-aware A-share research workflow powered by Zhitu Data Service APIs.
>
> 一个基于智兔数服 API、强调基本面证据和风险约束的 A 股研究工作流。

## 中文说明

### 项目简介

本项目是一个面向 Codex 的股票分析 Skill，用于调用智兔数服 API 完成单股分析、批量筛选、市场复盘和候选股研究。

默认研究范围仅包括用户可交易的沪深主板 A 股，并硬性排除：

- 创业板：`300`、`301` 开头；
- 科创板：`688`、`689` 开头；
- `ST`、`*ST` 及其他风险警示股票；
- 北交所和无法确认属于沪深主板的证券。

本项目不是“根据题材热度推荐股票”的工具。它要求同时验证基本面、行业地位、催化业务收入占比、业绩弹性、订单、产能及一手资料完整性。

### 主要功能

- 单只或批量 A 股行情分析；
- 沪深主板交易资格过滤；
- 股票列表和 ST 清单过滤；
- 行情、股票池和财务数据的确定性质量校验；
- 数据时效、Point-in-Time、复权口径和缺失原因管理；
- 实时行情、历史行情及技术指标诊断；
- 涨停、跌停、炸板和板块延续性复盘；
- 每次分析固定输出板块轮动位置，区分启动、强化、加速、分化、退潮和反弹；
- 按轮动阶段筛选对应沪深主板候选，并输出推荐理由、反证、分批仓位、确认及失效条件；
- 财务报表、财务指标、股东及股本分析；
- 公告、财报、公司官网和调研记录证据评分；
- 行业地位、收入占比、订单和产能验证；
- 美股、日本、韩国、港股、汇率、利率、商品、海外政策及地缘风险分析；
- 每次分析固定输出大盘、流动性、市场宽度及海外交易时段详情；
- 将“次日涨停”“次日上涨”“五日超额收益”作为不同研究目标；
- 输出透明评分、证据缺口、反方观点和失效条件。

### 评分原则

研究评分由以下部分组成：

| 维度 | 分值 |
|---|---:|
| 基本面与行业地位 | 25 |
| 商业兑现与业绩弹性 | 20 |
| 一手证据覆盖度 | 20 |
| 市场结构与相对强弱 | 15 |
| 海外与宏观适配 | 10 |
| 估值与下行风险 | 10 |

题材热度最多贡献总分 5 分。缺少财报、公告、官网、调研记录、订单或产能验证时会执行降分或总分封顶。

### 安装

在 Windows PowerShell 中执行：

```powershell
.\install-zhitu-stock-analysis.ps1
```

脚本会将 Skill 安装到：

```text
%USERPROFILE%\.codex\skills\zhitu-stock-analysis
```

### 配置智兔 Token

复制示例配置：

```powershell
Copy-Item .env.example .env.local
```

然后在 `.env.local` 中配置：

```dotenv
ZHITU_API_TOKEN=replace_with_your_zhitu_token
```

不要将真实 Token 写入 `SKILL.md`、浏览器端代码、公开日志或 Git 仓库。生产环境应使用服务器环境变量或密钥管理服务。

### 连接测试

```powershell
python .\work\skills\zhitu-stock-analysis\scripts\test_connection.py
```

测试脚本会检查股票列表、ST 清单、单股实时行情和财务指标接口，并输出数据质量分和异常代码；不会输出 Token 或完整响应内容。

也可以校验已保存的 JSON：

```powershell
python .\work\skills\zhitu-stock-analysis\scripts\data_quality.py quote quote.json
```

### 项目结构

```text
.
├── README.md
├── .env.example
├── install-zhitu-stock-analysis.ps1
├── outputs/
│   └── 智兔数服API可实现功能梳理.md
└── work/skills/zhitu-stock-analysis/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/
    │   ├── analysis-framework.md
    │   ├── data-quality-gates.md
    │   ├── global-risk-overlay.md
    │   └── zhitu-api.md
    └── scripts/
        ├── data_quality.py
        ├── test_connection.py
        └── test_data_quality.py
```

### 数据来源

- [智兔沪深 A 股 API](https://www.zhituapi.com/hsstockapi.html)
- [智兔沪深指数 API](https://www.zhituapi.com/hsindexapi.html)
- [智兔京市 A 股 API](https://www.zhituapi.com/bjdataapi.html)

公司事实和重大政策结论应进一步核验交易所公告、公司官网、政府及监管机构原文。

### 风险声明

本项目仅用于数据研究、软件开发和投资教育，不构成投资建议、收益保证或代客决策。评分代表研究优先级，不代表上涨概率。市场数据可能延迟、缺失或存在供应商口径差异，请在使用前核验数据许可、接口套餐和最新文档。

---

## English

### Overview

This repository provides a Codex skill for single-stock research, batch screening, market review, and candidate validation using Zhitu Data Service APIs.

The default tradable universe is limited to Shanghai and Shenzhen main-board A-shares. It excludes:

- ChiNext stocks with `300` or `301` prefixes;
- STAR Market stocks with `688` or `689` prefixes;
- `ST`, `*ST`, and other special-treatment securities;
- Beijing Stock Exchange securities and instruments that cannot be confirmed as Shanghai/Shenzhen main-board stocks.

The workflow does not rank stocks solely by theme popularity. Candidates must also be evaluated using fundamentals, industry position, catalyst-related revenue exposure, earnings sensitivity, order validation, capacity validation, and primary-source evidence.

### Features

- Single-stock and batch A-share analysis;
- Main-board eligibility and ST filtering;
- Deterministic quality checks for quotes, universes, and financial payloads;
- Freshness, point-in-time, adjustment, and missing-reason controls;
- Realtime and historical market-data diagnostics;
- Limit-up, limit-down, failed-limit, and sector follow-through review;
- Mandatory sector-rotation positioning for every analysis, including starting, strengthening, accelerating, diverging, fading, and rebounding stages;
- Rotation-linked main-board candidates with reasons, counter-evidence, staged model-portfolio exposure, confirmation, and invalidation conditions;
- Financial statement, ratio, capital, and shareholder analysis;
- Evidence scoring for filings, financial reports, official websites, and investor-relations records;
- Industry-position, revenue-exposure, order, and production-capacity validation;
- Global risk overlays covering US, Japanese, Korean, and Hong Kong markets, FX, rates, commodities, foreign policy, and geopolitical events;
- A mandatory market/global dashboard in every analysis, including liquidity, breadth, overseas session state, and timestamp alignment;
- Separate research labels for next-session limit-up, next-session positive return, and five-session excess return;
- Transparent component scores, evidence gaps, bear cases, and invalidation conditions.

### Scoring framework

| Dimension | Points |
|---|---:|
| Fundamentals and industry position | 25 |
| Commercial validation and earnings sensitivity | 20 |
| Primary-evidence coverage | 20 |
| Market structure and relative strength | 15 |
| Global and macro alignment | 10 |
| Valuation and downside risk | 10 |

Theme popularity contributes no more than five points to the total score. Missing financial reports, filings, official company evidence, investor-relations records, validated orders, or validated capacity triggers penalties or score caps.

### Installation

Run in Windows PowerShell:

```powershell
.\install-zhitu-stock-analysis.ps1
```

The installer copies the skill to:

```text
%USERPROFILE%\.codex\skills\zhitu-stock-analysis
```

### Token configuration

Create a local configuration file:

```powershell
Copy-Item .env.example .env.local
```

Set the server-side token:

```dotenv
ZHITU_API_TOKEN=replace_with_your_zhitu_token
```

Never place a real token in `SKILL.md`, browser-side code, public logs, or version control. Use environment variables or a secret manager in production.

### Connection test

```powershell
python .\work\skills\zhitu-stock-analysis\scripts\test_connection.py
```

The script checks the stock-list, ST-list, single-stock realtime, and financial-ratio endpoint families. It reports data-quality scores and issue codes while never printing the token or full API responses.

Validate a saved JSON payload with:

```powershell
python .\work\skills\zhitu-stock-analysis\scripts\data_quality.py quote quote.json
```

### Data sources

- [Zhitu Shanghai/Shenzhen Stock API](https://www.zhituapi.com/hsstockapi.html)
- [Zhitu Shanghai/Shenzhen Index API](https://www.zhituapi.com/hsindexapi.html)
- [Zhitu Beijing Stock API](https://www.zhituapi.com/bjdataapi.html)

Material company and policy claims should be verified against original exchange filings, company publications, and official government or regulatory sources.

### Disclaimer

This project is intended for data research, software development, and investment education only. It does not provide investment advice, guaranteed returns, or discretionary portfolio management. Scores represent research priority, not a probability of price appreciation. Market data may be delayed, incomplete, or vendor-specific; verify licensing, subscription entitlements, and current API documentation before use.

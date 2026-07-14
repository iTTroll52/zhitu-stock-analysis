#!/usr/bin/env python3
"""Generate a portable, self-contained HTML report from normalized analysis JSON."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


SIGNAL_LABELS = {
    "bottom_start": "底部启动",
    "accelerating": "加速候选",
    "limit_up": "涨停结构",
    "consecutive_limit_up": "连板结构",
}

STAGE_LABELS = {
    "starting": "启动",
    "strengthening": "强化",
    "accelerating": "加速",
    "diverging": "分化",
    "fading": "退潮",
    "rebounding": "反弹",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def safe_url(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} else ""


def tone_class(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        text = str(value or "").lower()
        if any(word in text for word in ("高", "强", "利好", "positive", "up")):
            return "up"
        if any(word in text for word in ("低", "弱", "利空", "negative", "down")):
            return "down"
        return "flat"
    return "up" if number > 0 else "down" if number < 0 else "flat"


def pct(value: Any) -> str:
    if value in (None, ""):
        return "—"
    if isinstance(value, str) and "%" in value:
        return esc(value)
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return esc(value)


def pills(items: Iterable[Any], css_class: str = "pill") -> str:
    return "".join(f'<span class="{css_class}">{esc(item)}</span>' for item in items)


def render_market(items: list[dict[str, Any]], empty: str) -> str:
    if not items:
        return f'<div class="empty">{esc(empty)}</div>'
    cards = []
    for item in items:
        change = item.get("change_pct", item.get("change"))
        cards.append(
            '<article class="tape-item">'
            f'<div class="tape-name">{esc(item.get("name", item.get("code", "—")))}</div>'
            f'<div class="tape-value">{esc(item.get("value", item.get("close", "—")))}</div>'
            f'<div class="tape-change {tone_class(change)}">{pct(change)}</div>'
            f'<div class="tape-note">{esc(item.get("session", item.get("note", "")))}</div>'
            '</article>'
        )
    return "".join(cards)


def render_rotation(rotation: dict[str, Any]) -> str:
    raw_stages = rotation.get("stages") or list(STAGE_LABELS)
    current = str(rotation.get("stage", rotation.get("current", ""))).lower()
    stage_html = []
    for index, item in enumerate(raw_stages, start=1):
        if isinstance(item, dict):
            key = str(item.get("key", item.get("stage", ""))).lower()
            label = item.get("label", STAGE_LABELS.get(key, key or "—"))
        else:
            key = str(item).lower()
            label = STAGE_LABELS.get(key, item)
        active = current in {key, str(label).lower()} or current == str(label)
        stage_html.append(
            f'<li class="rotation-step{" active" if active else ""}">'
            f'<span class="step-index">{index:02d}</span><strong>{esc(label)}</strong></li>'
        )
    leaders = pills(as_list(rotation.get("leaders")), "pill leader")
    strengthening = pills(as_list(rotation.get("strengthening")), "pill rising")
    fading = pills(as_list(rotation.get("fading")), "pill fading")
    return f"""
      <ol class="rotation-track">{''.join(stage_html)}</ol>
      <div class="rotation-copy">
        <div><span class="eyebrow">当前位置</span><strong class="rotation-current">{esc(rotation.get('current', STAGE_LABELS.get(current, current) or '待确认'))}</strong></div>
        <p>{esc(rotation.get('narrative', '缺少可验证的轮动描述。'))}</p>
      </div>
      <div class="rotation-groups">
        <div><span>领涨</span>{leaders or '<em>待确认</em>'}</div>
        <div><span>强化</span>{strengthening or '<em>待确认</em>'}</div>
        <div><span>退潮</span>{fading or '<em>待确认</em>'}</div>
      </div>
    """


def render_signals(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return '<div class="empty">未提供短线信号统计。</div>'
    blocks = []
    for signal in signals:
        key = str(signal.get("key", signal.get("signal", "")))
        label = signal.get("label", SIGNAL_LABELS.get(key, key or "未分类"))
        blocks.append(
            f'<article class="signal-block" data-signal="{esc(key)}">'
            f'<span class="signal-count">{esc(signal.get("count", "—"))}</span>'
            f'<h3>{esc(label)}</h3><p>{esc(signal.get("note", ""))}</p></article>'
        )
    return "".join(blocks)


def render_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return '<div class="empty">没有通过数据与证据闸门的候选。</div>'
    rows = []
    for item in candidates:
        signal = str(item.get("primary_signal", item.get("signal", "watch")))
        score = item.get("score", "—")
        reasons = as_list(item.get("reasons", item.get("reason")))
        exposure = item.get("exposure") if isinstance(item.get("exposure"), dict) else {}
        rows.append(
            f'<tr data-signal="{esc(signal)}">'
            f'<td><strong>{esc(item.get("name", "—"))}</strong><span class="code">{esc(item.get("code", ""))}</span></td>'
            f'<td><span class="signal-tag">{esc(SIGNAL_LABELS.get(signal, item.get("signal_label", signal)))}</span><small>{esc(item.get("sector", ""))}</small></td>'
            f'<td><span class="score">{esc(score)}</span><small>{esc(item.get("tier", ""))}</small></td>'
            f'<td>{"<br>".join(esc(reason) for reason in reasons) or "—"}</td>'
            f'<td><span class="exposure">初始 {esc(exposure.get("initial", item.get("initial_exposure", "—")))}</span>'
            f'<span class="exposure">确认 {esc(exposure.get("confirmation", item.get("confirmation_exposure", "—")))}</span>'
            f'<span class="exposure">上限 {esc(exposure.get("maximum", item.get("maximum_exposure", "—")))}</span></td>'
            f'<td><strong class="risk-text">{esc(item.get("no_chase", "—"))}</strong><small>{esc(item.get("invalidation", ""))}</small></td>'
            '</tr>'
        )
    return f"""
      <div class="filter-bar" aria-label="候选过滤">
        <button class="filter active" data-filter="all">全部</button>
        <button class="filter" data-filter="bottom_start">底部启动</button>
        <button class="filter" data-filter="accelerating">加速</button>
        <button class="filter" data-filter="limit_up">涨停</button>
        <button class="filter" data-filter="consecutive_limit_up">连板</button>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>标的</th><th>主信号 / 板块</th><th>评分</th><th>研究理由</th><th>模型仓位</th><th>不追 / 失效</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table></div>
    """


def render_evidence(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<div class="empty">未提供公告、财报、官网或调研证据。</div>'
    rows = []
    for item in items:
        status = str(item.get("status", "missing")).lower()
        rows.append(
            '<tr>'
            f'<td>{esc(item.get("category", "—"))}</td>'
            f'<td><span class="status {esc(status)}">{esc(item.get("label", status))}</span></td>'
            f'<td>{esc(item.get("summary", item.get("detail", "—")))}</td>'
            f'<td>{esc(item.get("available_at", item.get("date", "—")))}</td>'
            '</tr>'
        )
    return f'<div class="table-wrap"><table class="evidence-table"><thead><tr><th>证据类别</th><th>状态</th><th>结论</th><th>可得时间</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def render_list(items: list[Any], empty: str) -> str:
    if not items:
        return f'<li class="empty-line">{esc(empty)}</li>'
    return "".join(f'<li>{esc(item.get("text", item.get("summary", "")) if isinstance(item, dict) else item)}</li>' for item in items)


def render_sources(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<div class="empty">未提供可公开核验的来源链接。</div>'
    rows = []
    for index, item in enumerate(items, start=1):
        url = safe_url(item.get("url"))
        name = esc(item.get("name", item.get("title", f"来源 {index}")))
        title = f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{name}</a>' if url else name
        rows.append(
            f'<li><span>{index:02d}</span><div><strong>{title}</strong>'
            f'<small>{esc(item.get("kind", ""))} · {esc(item.get("published_at", item.get("date", "时间未提供")))}</small></div></li>'
        )
    return f'<ol class="sources">{"".join(rows)}</ol>'


def build_html(data: dict[str, Any]) -> str:
    quality = data.get("data_quality") if isinstance(data.get("data_quality"), dict) else {}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    rotation = data.get("rotation") if isinstance(data.get("rotation"), dict) else {}
    flags = as_list(quality.get("flags"))
    title = esc(data.get("title", "A股短线研究报告"))
    subtitle = esc(data.get("subtitle", "智兔市场数据 · 一手证据闸门 · 条件式候选"))
    candidates = [x for x in as_list(data.get("candidates")) if isinstance(x, dict)]
    report_json = json.dumps({"candidate_count": len(candidates)}, ensure_ascii=False)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{title}</title>
  <style>
    :root {{ --paper:#f4f0e7; --sheet:#fffdf7; --ink:#18211d; --muted:#6b716c; --line:#d9d4c9; --up:#b43a31; --down:#16705a; --amber:#9b6a18; --soft:#ebe6da; --shadow:0 18px 55px rgba(43,45,39,.10); font-synthesis:none; line-break:strict; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font-family:"Aptos","Microsoft YaHei UI","Noto Sans CJK SC",sans-serif; font-size:16px; line-height:1.72; }}
    body.dark {{ --paper:#171b18; --sheet:#202622; --ink:#eef0e8; --muted:#aeb6ae; --line:#3d443e; --soft:#2a312c; --shadow:none; }}
    h1,h2,h3,p {{ margin-top:0; }} h1,h2 {{ font-family:Georgia,"Noto Serif CJK SC","Songti SC",serif; font-weight:700; text-wrap:balance; }}
    p {{ text-wrap:pretty; }} button,a {{ font:inherit; }} a {{ color:inherit; text-underline-offset:3px; }}
    .topbar {{ position:sticky; top:0; z-index:20; display:flex; justify-content:space-between; align-items:center; padding:10px max(20px,calc((100vw - 1240px)/2)); border-bottom:1px solid color-mix(in oklch,var(--line) 72%,transparent); backdrop-filter:blur(18px); background:color-mix(in oklch,var(--paper) 84%,transparent); }}
    .brand {{ font-family:Georgia,"Noto Serif CJK SC",serif; font-weight:700; }} .top-actions {{ display:flex; gap:8px; }}
    .icon-button,.filter {{ min-height:40px; padding:8px 13px; border:1px solid var(--line); background:var(--sheet); color:var(--ink); cursor:pointer; }} .icon-button:hover,.filter:hover,.filter.active {{ border-color:var(--ink); }}
    main {{ width:min(1240px,calc(100% - 32px)); margin:36px auto 64px; }}
    .hero {{ position:relative; overflow:hidden; display:grid; grid-template-columns:1.6fr .7fr; gap:36px; min-height:360px; padding:clamp(28px,5vw,68px); background:var(--ink); color:var(--sheet); box-shadow:var(--shadow); }}
    .hero:after {{ content:""; position:absolute; right:-8%; bottom:-55%; width:42%; aspect-ratio:1; border:1px solid color-mix(in oklch,var(--sheet) 22%,transparent); border-radius:50%; box-shadow:0 0 0 44px color-mix(in oklch,var(--sheet) 4%,transparent),0 0 0 88px color-mix(in oklch,var(--sheet) 3%,transparent); }}
    .kicker,.eyebrow {{ display:block; margin-bottom:10px; color:var(--amber); font-size:12px; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }}
    .hero h1 {{ max-width:12em; margin-bottom:18px; font-size:clamp(2.45rem,1.5rem + 3.2vw,5.6rem); line-height:1.08; letter-spacing:-.02em; }} .hero p {{ max-width:38em; color:color-mix(in oklch,var(--sheet) 76%,transparent); }}
    .meta {{ display:grid; align-content:end; gap:14px; z-index:1; }} .meta div {{ display:flex; justify-content:space-between; gap:20px; padding-bottom:9px; border-bottom:1px solid color-mix(in oklch,var(--sheet) 18%,transparent); }} .meta span {{ color:color-mix(in oklch,var(--sheet) 62%,transparent); }}
    .quality {{ font-family:Georgia,serif; font-size:clamp(2rem,4vw,4rem); line-height:1; }}
    .section {{ margin-top:24px; padding:clamp(22px,3.3vw,42px); border:1px solid var(--line); background:var(--sheet); box-shadow:var(--shadow); }}
    .section-head {{ display:flex; justify-content:space-between; gap:24px; align-items:end; margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid var(--line); }} .section-head h2 {{ margin:0; font-size:clamp(1.65rem,1.2rem + 1.5vw,2.6rem); }} .section-head p {{ max-width:42em; margin:0; color:var(--muted); }}
    .tape {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr)); border-top:1px solid var(--line); border-left:1px solid var(--line); }} .tape-item {{ min-height:132px; padding:18px; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
    .tape-name,.tape-note,small {{ color:var(--muted); font-size:12px; }} .tape-value {{ margin-top:12px; font-family:Georgia,serif; font-size:24px; font-variant-numeric:tabular-nums; }} .tape-change {{ font-weight:800; font-variant-numeric:tabular-nums; }} .up {{ color:var(--up); }} .down {{ color:var(--down); }} .flat {{ color:var(--muted); }}
    .summary-grid {{ display:grid; grid-template-columns:1.25fr .75fr; gap:18px; }} .verdict {{ padding:26px; background:var(--soft); }} .verdict strong {{ display:block; margin-bottom:8px; font-family:Georgia,"Noto Serif CJK SC",serif; font-size:clamp(1.5rem,3vw,2.7rem); line-height:1.25; }} .flag-box {{ padding:24px; border:1px solid var(--line); }} .flags,.pill-row {{ display:flex; flex-wrap:wrap; gap:8px; }} .pill {{ display:inline-flex; padding:4px 9px; border:1px solid var(--line); font-size:12px; }}
    .rotation-track {{ display:grid; grid-template-columns:repeat(6,1fr); margin:0 0 28px; padding:0; list-style:none; border:1px solid var(--line); }} .rotation-step {{ position:relative; min-height:98px; padding:16px; border-right:1px solid var(--line); color:var(--muted); }} .rotation-step:last-child {{ border-right:0; }} .rotation-step.active {{ background:var(--ink); color:var(--sheet); }} .step-index {{ display:block; margin-bottom:20px; font:12px/1 monospace; }}
    .rotation-copy {{ display:grid; grid-template-columns:.45fr 1fr; gap:28px; align-items:start; }} .rotation-current {{ display:block; font-family:Georgia,"Noto Serif CJK SC",serif; font-size:2.5rem; }} .rotation-copy p {{ color:var(--muted); }} .rotation-groups {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:20px; }} .rotation-groups>div {{ padding:16px; background:var(--soft); }} .rotation-groups>div>span {{ display:block; margin-bottom:10px; color:var(--muted); font-size:12px; }} .rotation-groups em {{ color:var(--muted); font-style:normal; font-size:13px; }}
    .signal-grid {{ display:grid; grid-template-columns:repeat(4,1fr); border-top:1px solid var(--line); border-left:1px solid var(--line); }} .signal-block {{ min-height:190px; padding:24px; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }} .signal-count {{ display:block; font:700 3.4rem/1 Georgia,serif; }} .signal-block h3 {{ margin:25px 0 8px; }} .signal-block p {{ color:var(--muted); font-size:14px; }}
    .filter-bar {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; }} .filter {{ background:transparent; }} .table-wrap {{ overflow:auto; border:1px solid var(--line); }} table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }} th,td {{ padding:15px 14px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }} th {{ color:var(--muted); font-size:12px; letter-spacing:.07em; white-space:nowrap; }} td {{ min-width:112px; }} td:nth-child(4) {{ min-width:250px; }} tr:last-child td {{ border-bottom:0; }} .code,td small,.exposure {{ display:block; margin-top:5px; }} .signal-tag,.status {{ display:inline-flex; padding:3px 7px; background:var(--soft); font-size:12px; }} .score {{ font:700 2rem/1 Georgia,serif; }} .exposure {{ white-space:nowrap; }} .risk-text {{ color:var(--up); }}
    .status.confirmed,.status.pass,.status.verified {{ color:var(--down); }} .status.missing,.status.failed,.status.risk {{ color:var(--up); }} .status.pending,.status.partial {{ color:var(--amber); }}
    .thesis-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }} .thesis {{ padding:24px; border:1px solid var(--line); }} .thesis.bull {{ border-top:5px solid var(--up); }} .thesis.bear {{ border-top:5px solid var(--down); }} .thesis ul,.risk-list {{ margin:0; padding-left:1.25em; }} .thesis li,.risk-list li {{ margin:8px 0; }}
    .sources {{ margin:0; padding:0; list-style:none; }} .sources li {{ display:grid; grid-template-columns:38px 1fr; gap:12px; padding:13px 0; border-bottom:1px solid var(--line); }} .sources li>span {{ color:var(--muted); font:12px/1.7 monospace; }} .sources small {{ display:block; }}
    .empty {{ padding:22px; border:1px dashed var(--line); color:var(--muted); }} .empty-line {{ color:var(--muted); }} .disclaimer {{ margin-top:24px; padding:22px; color:var(--muted); font-size:13px; border-top:1px solid var(--line); }}
    [hidden] {{ display:none!important; }}
    @media (max-width:900px) {{ .hero,.summary-grid,.rotation-copy,.thesis-grid {{ grid-template-columns:1fr; }} .rotation-track {{ grid-template-columns:repeat(3,1fr); }} .rotation-step:nth-child(3) {{ border-right:0; }} .rotation-groups,.signal-grid {{ grid-template-columns:repeat(2,1fr); }} }}
    @media (max-width:580px) {{ main {{ width:min(100% - 20px,1240px); margin-top:14px; }} .topbar {{ padding:8px 10px; }} .brand {{ font-size:13px; }} .hero {{ padding:26px 20px; }} .section {{ padding:20px 14px; }} .section-head {{ display:block; }} .section-head p {{ margin-top:8px; }} .rotation-track,.rotation-groups,.signal-grid {{ grid-template-columns:1fr; }} .rotation-step {{ border-right:0; }} .signal-block {{ min-height:auto; }} }}
    @media print {{ body {{ background:#fff; color:#111; }} .topbar,.filter-bar {{ display:none; }} main {{ width:100%; margin:0; }} .hero,.section {{ break-inside:avoid; box-shadow:none; }} .hero {{ min-height:auto; }} a {{ text-decoration:none; }} }}
  </style>
</head>
<body>
  <header class="topbar"><div class="brand">ZHITU · SHORT-HORIZON RESEARCH</div><div class="top-actions"><button class="icon-button" id="theme">明暗</button><button class="icon-button" onclick="window.print()">打印 / PDF</button></div></header>
  <main>
    <section class="hero" id="top"><div><span class="kicker">Research report · 非收益承诺</span><h1>{title}</h1><p>{subtitle}</p></div><div class="meta">
      <div><span>数据截止</span><strong>{esc(data.get('data_cutoff','未提供'))}</strong></div>
      <div><span>生成时间</span><strong>{esc(data.get('generated_at','未提供'))}</strong></div>
      <div><span>市场状态</span><strong>{esc(data.get('market_session','待确认'))}</strong></div>
      <div><span>数据质量</span><strong class="quality">{esc(quality.get('score','—'))}</strong></div>
      <div><span>研究层级</span><strong>{esc(data.get('research_tier',summary.get('tier','观察级')))}</strong></div>
    </div></section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">01 · MARKET TAPE</span><h2>大盘与海外传导</h2></div><p>同一分析必须标明交易时段与时间戳，避免把昨夜收盘和今日盘中混在一起。</p></div>
      <div class="tape">{render_market([x for x in as_list(data.get('market')) if isinstance(x,dict)],'未提供大盘快照。')}</div>
      <div style="height:12px"></div><div class="tape">{render_market([x for x in as_list(data.get('global')) if isinstance(x,dict)],'未提供海外市场、汇率、利率或商品数据。')}</div>
    </section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">02 · EXECUTIVE VIEW</span><h2>一句话结论与质量边界</h2></div><p>{esc(summary.get('confidence','信号只代表研究优先级，不代表上涨概率。'))}</p></div>
      <div class="summary-grid"><div class="verdict"><strong>{esc(summary.get('verdict','当前不形成高置信度结论'))}</strong><p>{esc(summary.get('key_reason','请补充实时行情、轮动和一手证据。'))}</p></div>
      <div class="flag-box"><span class="eyebrow">数据质量标记</span><div class="flags">{pills(flags) or '<span class="pill">无明确标记</span>'}</div></div></div>
    </section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">03 · ROTATION</span><h2>板块轮动：现在轮到哪里</h2></div><p>阶段判断必须同时给出支持证据与反证，不把单日冲高直接称为主升。</p></div>{render_rotation(rotation)}</section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">04 · SIGNAL MAP</span><h2>底部启动、加速、涨停与连板</h2></div><p>四类信号分开统计；同一标的只指定一个主标签，避免重复计数夸大强度。</p></div><div class="signal-grid">{render_signals([x for x in as_list(data.get('signals')) if isinstance(x,dict)])}</div></section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">05 · CANDIDATES</span><h2>条件式候选与模型仓位</h2></div><p>仅展示沪深主板且非 ST 的候选；仓位是研究用模型区间，必须与确认条件和失效条件配套。</p></div>{render_candidates(candidates)}</section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">06 · EVIDENCE</span><h2>公告、财报、官网与调研证据</h2></div><p>缺少订单、产能、收入占比或一手资料时必须降分或封顶，题材热度不能补足证据缺口。</p></div>{render_evidence([x for x in as_list(data.get('evidence')) if isinstance(x,dict)])}</section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">07 · TWO-SIDED VIEW</span><h2>正反逻辑与失效条件</h2></div><p>把最强反方解释与风险前置，避免把分析写成只支持买入的单向叙事。</p></div>
      <div class="thesis-grid"><article class="thesis bull"><h3>支持逻辑</h3><ul>{render_list(as_list(data.get('bull_case')),'未提供可验证的支持逻辑。')}</ul></article><article class="thesis bear"><h3>反方逻辑</h3><ul>{render_list(as_list(data.get('bear_case')),'未提供有力度的反方解释。')}</ul></article></div>
      <div class="flag-box" style="margin-top:18px"><h3>风险与失效</h3><ul class="risk-list">{render_list(as_list(data.get('risks',data.get('invalidation'))),'未提供明确失效条件。')}</ul></div>
    </section>

    <section class="section"><div class="section-head"><div><span class="eyebrow">08 · SOURCES</span><h2>来源与可追溯性</h2></div><p>市场数据注明智兔返回时间；公司与政策事实优先链接交易所、公司、政府或监管原文。</p></div>{render_sources([x for x in as_list(data.get('sources')) if isinstance(x,dict)])}</section>
    <footer class="disclaimer">{esc(data.get('disclaimer','本报告仅用于数据研究、软件开发和投资教育，不构成投资建议、收益保证或代客决策。市场数据可能延迟、缺失或存在供应商口径差异。'))}</footer>
  </main>
  <script type="application/json" id="report-meta">{esc(report_json)}</script>
  <script>
    const themeButton=document.getElementById('theme');
    const savedTheme=localStorage.getItem('zhitu-report-theme');
    if(savedTheme==='dark') document.body.classList.add('dark');
    themeButton.addEventListener('click',()=>{{document.body.classList.toggle('dark');localStorage.setItem('zhitu-report-theme',document.body.classList.contains('dark')?'dark':'light');}});
    document.querySelectorAll('.filter').forEach(button=>button.addEventListener('click',()=>{{
      document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active')); button.classList.add('active');
      const target=button.dataset.filter; document.querySelectorAll('tbody tr[data-signal]').forEach(row=>row.hidden=target!=='all'&&row.dataset.signal!==target);
    }}));
  </script>
</body>
</html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a self-contained Zhitu stock-analysis HTML report.")
    parser.add_argument("input", type=Path, help="Normalized analysis JSON file")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Destination .html file")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit("Input JSON root must be an object.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(data), encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.output.resolve()), "bytes": args.output.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

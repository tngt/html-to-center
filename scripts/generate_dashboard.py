#!/usr/bin/env python3
"""
generate_dashboard.py - 从 registry.json 生成 dashboard HTML

用法：
  python generate_dashboard.py
  python generate_dashboard.py --output /path/to/index.html
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

CONFIG_PATH = Path.home() / ".config" / "html-to-center" / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        print(f"Error: config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)

def load_registry(registry_path: Path) -> dict:
    if not registry_path.exists():
        return {"meta": {}, "summary": {}, "files": []}
    with open(registry_path, encoding="utf-8") as f:
        return json.load(f)

def generate_html(registry: dict) -> str:
    files = registry.get("files", [])
    summary = registry.get("summary", {})
    meta = registry.get("meta", {})

    # 计算统计数据
    # 月度产出（最近6个月）
    monthly = defaultdict(int)
    for f in files:
        d = f.get("registered_at", "")
        if d:
            month = d[:7]  # YYYY-MM
            monthly[month] += 1
    last_6_months = sorted(monthly.keys())[-6:]
    monthly_data = [{"month": m, "count": monthly[m]} for m in last_6_months]

    # 主题趋势（top 5 主题，按月统计）
    topic_monthly = defaultdict(lambda: defaultdict(int))
    for f in files:
        topic = f.get("topic", "其他")
        d = f.get("registered_at", "")
        if d and topic:
            topic_monthly[topic][d[:7]] += 1

    all_topics = sorted(topic_monthly.keys(), key=lambda t: sum(topic_monthly[t].values()), reverse=True)[:5]
    trend_months = sorted(set(m for t in all_topics for m in topic_monthly[t].keys()))[-6:]
    trend_data = {
        "months": trend_months,
        "topics": [
            {"name": t, "values": [topic_monthly[t].get(m, 0) for m in trend_months]}
            for t in all_topics
        ]
    }

    # 热力图数据（最近52周）
    heatmap = {}
    for f in files:
        d = f.get("registered_at", "")
        if d:
            heatmap[d] = heatmap.get(d, 0) + 1
    today = datetime.now().date()
    start = today - timedelta(weeks=52)
    heatmap_data = []
    d = start
    while d <= today:
        ds = d.strftime("%Y-%m-%d")
        heatmap_data.append({"date": ds, "count": heatmap.get(ds, 0)})
        d += timedelta(days=1)

    # 项目活跃度
    project_activity = defaultdict(lambda: {"count": 0, "last_date": ""})
    for f in files:
        p = f.get("project", "未分类")
        project_activity[p]["count"] += 1
        d = f.get("registered_at", "")
        if d > project_activity[p]["last_date"]:
            project_activity[p]["last_date"] = d
    projects_sorted = sorted(project_activity.items(), key=lambda x: x[1]["last_date"], reverse=True)[:8]

    # 序列化数据
    files_json = json.dumps(files, ensure_ascii=False)
    monthly_json = json.dumps(monthly_data, ensure_ascii=False)
    trend_json = json.dumps(trend_data, ensure_ascii=False)
    heatmap_json = json.dumps(heatmap_data, ensure_ascii=False)
    projects_json = json.dumps([{"name": k, **v} for k, v in projects_sorted], ensure_ascii=False)
    summary_text = summary.get("content") or "暂无研究摘要，运行摘要生成后将在此显示。"
    summary_week = summary.get("week") or ""
    total = meta.get("total_files", len(files))
    last_updated = meta.get("last_updated", "")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>html-to-center</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif; min-height: 100vh; transition: background 0.2s, color 0.2s; }}
  a {{ color: inherit; text-decoration: none; }}

  /* 亮色主题（默认） */
  body.light {{ background: #f5f5f5; color: #1a1a1a; }}
  body.light .nav {{ background: #fff; border-bottom-color: #e8e8e8; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  body.light .nav-title {{ color: #1a1a1a; }}
  body.light .nav-meta {{ color: #999; }}
  body.light .search {{ background: #f7f7f7; border-color: #e0e0e0; color: #1a1a1a; }}
  body.light .search:focus {{ border-color: #bbb; background: #fff; }}
  body.light .search::placeholder {{ color: #bbb; }}
  body.light .theme-btn {{ background: #fff; border-color: #e0e0e0; color: #666; }}
  body.light .theme-btn:hover {{ border-color: #bbb; color: #333; }}
  body.light .card {{ background: #fff; border-color: #e8e8e8; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }}
  body.light .card-title {{ color: #aaa; }}
  body.light .card-value {{ color: #1a1a1a; }}
  body.light .summary-week {{ color: #bbb; }}
  body.light .summary-text {{ color: #555; }}
  body.light .heatmap-y-label, body.light .heatmap-x-label {{ color: #bbb; }}
  body.light .heatmap-day {{ background: #eee; }}
  body.light .heatmap-day[data-count="1"] {{ background: #c6e9d4; }}
  body.light .heatmap-day[data-count="2"] {{ background: #8dd4ae; }}
  body.light .heatmap-day[data-count="3"] {{ background: #4db882; }}
  body.light .heatmap-day[data-count="4"] {{ background: #2a9d62; }}
  body.light .heatmap-day[data-count="5"] {{ background: #1a7a48; }}
  body.light .filter-btn {{ background: #fff; border-color: #e0e0e0; color: #888; }}
  body.light .filter-btn:hover, body.light .filter-btn.active {{ background: #f0f0f0; border-color: #ccc; color: #333; }}
  body.light .filter-label {{ color: #ccc; }}
  body.light .file-card {{ background: #fff; border-color: #e8e8e8; }}
  body.light .file-card:hover {{ border-color: #ccc; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  body.light .file-type.html {{ background: #e8f2fc; color: #2d7cc7; }}
  body.light .file-type.md {{ background: #e8f5ee; color: #2a8a52; }}
  body.light .file-name {{ color: #1a1a1a; }}
  body.light .file-meta {{ color: #aaa; }}
  body.light .file-desc {{ color: #888; }}
  body.light .file-tag {{ background: #f5f5f5; border-color: #e8e8e8; color: #999; }}
  body.light .file-date {{ color: #ccc; }}
  body.light .empty {{ color: #ccc; }}

  /* 暗色主题 */
  body.dark {{ background: #0d0d0d; color: #e0e0e0; }}
  body.dark .nav {{ background: #0d0d0d; border-bottom-color: #1e1e1e; box-shadow: none; }}
  body.dark .nav-title {{ color: #fff; }}
  body.dark .nav-meta {{ color: #555; }}
  body.dark .search {{ background: #161616; border-color: #2a2a2a; color: #e0e0e0; }}
  body.dark .search:focus {{ border-color: #444; background: #161616; }}
  body.dark .search::placeholder {{ color: #444; }}
  body.dark .theme-btn {{ background: #1a1a1a; border-color: #2a2a2a; color: #999; }}
  body.dark .theme-btn:hover {{ border-color: #555; color: #ccc; }}
  body.dark .card {{ background: #111; border-color: #1e1e1e; box-shadow: none; }}
  body.dark .card-title {{ color: #555; }}
  body.dark .card-value {{ color: #fff; }}
  body.dark .summary-week {{ color: #555; }}
  body.dark .summary-text {{ color: #aaa; }}
  body.dark .heatmap-y-label, body.dark .heatmap-x-label {{ color: #444; }}
  body.dark .heatmap-day {{ background: #1a1a1a; }}
  body.dark .heatmap-day[data-count="1"] {{ background: #1a3a2a; }}
  body.dark .heatmap-day[data-count="2"] {{ background: #1e5c3a; }}
  body.dark .heatmap-day[data-count="3"] {{ background: #25804f; }}
  body.dark .heatmap-day[data-count="4"] {{ background: #2da062; }}
  body.dark .heatmap-day[data-count="5"] {{ background: #3dc27a; }}
  body.dark .filter-btn {{ background: #111; border-color: #222; color: #777; }}
  body.dark .filter-btn:hover, body.dark .filter-btn.active {{ background: #1e1e1e; border-color: #3d3d3d; color: #ccc; }}
  body.dark .filter-label {{ color: #444; }}
  body.dark .file-card {{ background: #111; border-color: #1e1e1e; }}
  body.dark .file-card:hover {{ border-color: #333; box-shadow: none; }}
  body.dark .file-type.html {{ background: #1a2a3a; color: #5a9fd4; }}
  body.dark .file-type.md {{ background: #1a2a1a; color: #5abf7a; }}
  body.dark .file-name {{ color: #ddd; }}
  body.dark .file-meta {{ color: #555; }}
  body.dark .file-desc {{ color: #777; }}
  body.dark .file-tag {{ background: #1a1a1a; border-color: #2a2a2a; color: #666; }}
  body.dark .file-date {{ color: #444; }}
  body.dark .empty {{ color: #444; }}

  /* 共통 레이아웃 */
  .nav {{ display: flex; align-items: center; justify-content: space-between; padding: 16px 32px; border-bottom: 1px solid; position: sticky; top: 0; z-index: 100; }}
  .nav-title {{ font-size: 15px; font-weight: 600; letter-spacing: 0.02em; }}
  .nav-meta {{ font-size: 12px; }}
  .nav-right {{ display: flex; align-items: center; gap: 12px; }}
  .search-wrap {{ flex: 1; max-width: 320px; margin: 0 32px; }}
  .search {{ width: 100%; border-radius: 6px; padding: 7px 12px; font-size: 13px; outline: none; border: 1px solid; }}
  .theme-btn {{ font-size: 12px; padding: 6px 14px; border-radius: 6px; border: 1px solid; cursor: pointer; white-space: nowrap; }}
  .main {{ padding: 24px 32px; max-width: 1400px; margin: 0 auto; }}
  .profile {{ display: grid; grid-template-columns: 2fr 1fr 1fr; grid-template-rows: auto auto; gap: 16px; margin-bottom: 24px; }}
  .card {{ border: 1px solid; border-radius: 10px; padding: 20px; }}
  .card-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px; }}
  .card-value {{ font-size: 28px; font-weight: 700; }}
  .card-sub {{ font-size: 12px; margin-top: 4px; }}
  .summary-card {{ grid-column: 1; grid-row: 1 / 3; }}
  .summary-week {{ font-size: 11px; margin-bottom: 8px; }}
  .summary-text {{ font-size: 14px; line-height: 1.8; }}
  .heatmap-card {{ grid-column: 2 / 4; grid-row: 2; }}
  .heatmap-wrap {{ display: flex; gap: 6px; }}
  .heatmap-y-labels {{ display: flex; flex-direction: column; justify-content: space-around; padding: 0 4px 0 0; }}
  .heatmap-y-label {{ font-size: 9px; height: 12px; line-height: 12px; }}
  .heatmap-right {{ flex: 1; overflow: hidden; }}
  .heatmap-x-labels {{ display: flex; gap: 2px; margin-bottom: 3px; overflow: hidden; }}
  .heatmap-x-label {{ font-size: 9px; width: 12px; text-align: center; flex-shrink: 0; }}
  .heatmap {{ display: flex; gap: 2px; flex-wrap: nowrap; }}
  .heatmap-week {{ display: flex; flex-direction: column; gap: 2px; }}
  .heatmap-day {{ width: 10px; height: 10px; border-radius: 2px; }}
  canvas {{ width: 100%; height: 120px; }}
  .filters {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }}
  .filter-btn {{ font-size: 12px; padding: 5px 12px; border-radius: 20px; border: 1px solid; cursor: pointer; transition: all 0.15s; }}
  .filter-label {{ font-size: 11px; margin-right: 4px; }}
  .files-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }}
  .file-card {{ border: 1px solid; border-radius: 8px; padding: 16px; cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s; }}
  .file-type {{ display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .file-name {{ font-size: 13px; font-weight: 500; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .file-meta {{ font-size: 11px; margin-bottom: 6px; }}
  .file-desc {{ font-size: 12px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 8px; }}
  .file-tags {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .file-tag {{ font-size: 10px; padding: 2px 7px; border: 1px solid; border-radius: 3px; }}
  .file-date {{ font-size: 10px; margin-top: 8px; }}
  .empty {{ text-align: center; padding: 60px; font-size: 14px; }}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-title">html-to-center</div>
  <div class="search-wrap">
    <input class="search" id="search" type="text" placeholder="搜索文件、项目、标签..." oninput="filterFiles()">
  </div>
  <div class="nav-right">
    <div class="nav-meta">共 {total} 个文件 · 更新于 {last_updated}</div>
    <button class="theme-btn" id="themeBtn" onclick="toggleTheme()">暗色</button>
  </div>
</nav>

<div class="main">

  <!-- 个人画像区 -->
  <div class="profile">

    <!-- 研究摘要 -->
    <div class="card summary-card">
      <div class="card-title">研究摘要</div>
      <div class="summary-week">{summary_week}</div>
      <div class="summary-text">{summary_text}</div>
    </div>

    <!-- 主题趋势 -->
    <div class="card">
      <div class="card-title">主题趋势</div>
      <canvas id="trendChart"></canvas>
    </div>

    <!-- 月度产出 -->
    <div class="card">
      <div class="card-title">月度产出</div>
      <canvas id="monthlyChart"></canvas>
    </div>

    <!-- 项目活跃度 -->
    <div class="card" style="grid-column: 2; grid-row: 2;">
      <div class="card-title">项目活跃度</div>
      <div id="projectList" style="margin-top:4px;"></div>
    </div>

    <!-- 热力图 -->
    <div class="card heatmap-card">
      <div class="card-title">收录热力图</div>
      <div class="heatmap-wrap">
        <div class="heatmap-y-labels" id="heatmapYLabels"></div>
        <div class="heatmap-right">
          <div class="heatmap-x-labels" id="heatmapXLabels"></div>
          <div class="heatmap" id="heatmap"></div>
        </div>
      </div>
    </div>

  </div>

  <!-- 过滤器 -->
  <div class="filters" id="filters">
    <span class="filter-label">项目</span>
    <button class="filter-btn active" onclick="setProjectFilter('', this)">全部</button>
  </div>

  <!-- 文件卡片区 -->
  <div class="files-grid" id="filesGrid"></div>

</div>

<script>
// 主题切换
const savedTheme = localStorage.getItem('htc-theme') || 'light';
document.body.className = savedTheme;
function toggleTheme() {{
  const next = document.body.classList.contains('light') ? 'dark' : 'light';
  document.body.className = next;
  localStorage.setItem('htc-theme', next);
  document.getElementById('themeBtn').textContent = next === 'light' ? '暗色' : '亮色';
  setTimeout(() => {{ renderMonthly(); renderTrend(); renderProjects(); }}, 50);
}}
document.addEventListener('DOMContentLoaded', () => {{
  document.getElementById('themeBtn').textContent = savedTheme === 'light' ? '暗色' : '亮色';
}});

const FILES = {files_json};
const MONTHLY = {monthly_json};
const TREND = {trend_json};
const HEATMAP = {heatmap_json};
const PROJECTS = {projects_json};

let currentProject = '';
let currentSearch = '';

// 从 hash 读取初始过滤参数
const hashFilter = window.location.hash.replace('#filter=', '');
if (hashFilter) currentSearch = decodeURIComponent(hashFilter);

// 渲染热力图
function renderHeatmap() {{
  const el = document.getElementById('heatmap');
  const xLabelsEl = document.getElementById('heatmapXLabels');
  const yLabelsEl = document.getElementById('heatmapYLabels');

  // Y轴：星期标签（一列7格，显示一三五）
  const dayLabels = ['日','一','二','三','四','五','六'];
  [0,2,4,6].forEach(i => {{
    const label = document.createElement('div');
    label.className = 'heatmap-y-label';
    label.textContent = dayLabels[i];
    // 每格12px + gap 2px = 14px，空行用空字符填位
    yLabelsEl.style.gap = '2px';
    yLabelsEl.appendChild(label);
    if (i < 6) {{
      const spacer = document.createElement('div');
      spacer.className = 'heatmap-y-label';
      yLabelsEl.appendChild(spacer);
    }}
  }});

  const weeks = [];
  let week = [];
  HEATMAP.forEach((d) => {{
    week.push(d);
    if (week.length === 7) {{ weeks.push(week); week = []; }}
  }});
  if (week.length) weeks.push(week);

  // X轴：每隔4周显示一次月份
  weeks.forEach((w, wi) => {{
    const label = document.createElement('div');
    label.className = 'heatmap-x-label';
    const firstDate = w[0].date;
    const month = parseInt(firstDate.slice(5, 7));
    // 每月第一周显示月份
    const prevWeekDate = wi > 0 ? weeks[wi-1][0].date : '';
    const prevMonth = prevWeekDate ? parseInt(prevWeekDate.slice(5, 7)) : -1;
    label.textContent = (month !== prevMonth) ? month + '月' : '';
    xLabelsEl.appendChild(label);
  }});

  weeks.forEach(w => {{
    const col = document.createElement('div');
    col.className = 'heatmap-week';
    w.forEach(d => {{
      const cell = document.createElement('div');
      cell.className = 'heatmap-day';
      const c = Math.min(d.count, 5);
      if (c > 0) cell.setAttribute('data-count', c);
      cell.title = d.date + ': ' + d.count + ' 个文件';
      col.appendChild(cell);
    }});
    el.appendChild(col);
  }});
}}

// 渲染月度柱状图
function renderMonthly() {{
  const canvas = document.getElementById('monthlyChart');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth * 2;
  canvas.height = 240;
  const w = canvas.width, h = canvas.height;
  const pad = 20;
  const max = Math.max(...MONTHLY.map(d => d.count), 1);
  const barW = (w - pad * 2) / MONTHLY.length * 0.6;
  const gap = (w - pad * 2) / MONTHLY.length;

  ctx.fillStyle = '#4db882';
  MONTHLY.forEach((d, i) => {{
    const bh = (d.count / max) * (h - pad * 2);
    const x = pad + i * gap + gap * 0.2;
    const y = h - pad - bh;
    ctx.fillRect(x, y, barW, bh);
  }});

  ctx.fillStyle = '#bbb';
  ctx.font = '20px sans-serif';
  MONTHLY.forEach((d, i) => {{
    const x = pad + i * gap + gap * 0.2;
    ctx.fillText(d.month.slice(5), x, h - 4);
  }});
}}

// 渲染主题趋势折线图
function renderTrend() {{
  const canvas = document.getElementById('trendChart');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth * 2;
  canvas.height = 240;
  const w = canvas.width, h = canvas.height;
  const pad = 20;
  const months = TREND.months;
  const topics = TREND.topics;
  if (!months.length) return;

  const max = Math.max(...topics.flatMap(t => t.values), 1);
  const colors = ['#3dc27a','#5a9fd4','#f0a050','#d45a8a','#a07ad4'];

  topics.forEach((topic, ti) => {{
    ctx.strokeStyle = colors[ti % colors.length];
    ctx.lineWidth = 2;
    ctx.beginPath();
    topic.values.forEach((v, i) => {{
      const x = pad + i * (w - pad * 2) / (months.length - 1 || 1);
      const y = h - pad - (v / max) * (h - pad * 2);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }});
    ctx.stroke();
  }});
}}

// 渲染项目活跃度
function renderProjects() {{
  const el = document.getElementById('projectList');
  const max = Math.max(...PROJECTS.map(p => p.count), 1);
  el.innerHTML = PROJECTS.map(p => `
    <div style="margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
        <span style="color:#aaa;">${{p.name}}</span>
        <span style="color:#555;">${{p.count}}</span>
      </div>
      <div style="height:3px;background:#1a1a1a;border-radius:2px;">
        <div style="height:3px;background:#2da062;border-radius:2px;width:${{(p.count/max*100).toFixed(0)}}%;"></div>
      </div>
    </div>
  `).join('');
}}

// 渲染项目过滤器
function renderFilters() {{
  const filters = document.getElementById('filters');
  const projects = [...new Set(FILES.map(f => f.project).filter(Boolean))];
  projects.forEach(p => {{
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.textContent = p;
    btn.onclick = () => setProjectFilter(p, btn);
    filters.appendChild(btn);
  }});
}}

function setProjectFilter(project, btn) {{
  currentProject = project;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterFiles();
}}

// 过滤并渲染文件卡片
function filterFiles() {{
  const search = document.getElementById('search').value.toLowerCase() || currentSearch.toLowerCase();
  currentSearch = search;

  const filtered = FILES.filter(f => {{
    const matchProject = !currentProject || f.project === currentProject;
    const matchSearch = !search || [f.filename, f.project, f.topic, f.description, ...(f.tags||[])].some(v => v && v.toLowerCase().includes(search));
    return matchProject && matchSearch;
  }});

  const grid = document.getElementById('filesGrid');
  if (!filtered.length) {{
    grid.innerHTML = '<div class="empty">没有找到匹配的文件</div>';
    return;
  }}

  grid.innerHTML = filtered.map(f => `
    <div class="file-card" onclick="openFile('${{f.path}}')">
      <div class="file-type ${{f.type}}">${{f.type}}</div>
      <div class="file-name" title="${{f.filename}}">${{f.filename}}</div>
      <div class="file-meta">${{f.project || ''}}${{f.project && f.topic ? ' · ' : ''}}${{f.topic || ''}}</div>
      <div class="file-desc">${{f.description || ''}}</div>
      ${{f.tags && f.tags.length ? `<div class="file-tags">${{f.tags.map(t => `<span class="file-tag">${{t}}</span>`).join('')}}</div>` : ''}}
      <div class="file-date">${{f.registered_at}}</div>
    </div>
  `).join('');
}}

function openFile(path) {{
  window.open('file://' + path, '_blank');
}}

// 初始化
renderHeatmap();
renderFilters();
filterFiles();
if (document.getElementById('search').value === '' && currentSearch) {{
  document.getElementById('search').value = currentSearch;
}}

// 图表需要等 DOM 渲染完成后再绘制
setTimeout(() => {{
  renderMonthly();
  renderTrend();
  renderProjects();
}}, 100);
</script>
</body>
</html>"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="输出 HTML 文件路径")
    args = parser.parse_args()

    config = load_config()
    center_dir = Path(config["center_dir"])
    registry_path = center_dir / "registry.json"
    registry = load_registry(registry_path)

    html = generate_html(registry)

    output_path = args.output or str(center_dir / "dashboard" / "index.html")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard 已生成：{output_path}", file=sys.stderr)
    print(output_path)

if __name__ == "__main__":
    main()

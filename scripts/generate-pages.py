from __future__ import annotations

import html
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "flask_api" / "openapi_history"
OUTPUT_DIR = ROOT / "site"
OUTPUT_HISTORY_DIR = OUTPUT_DIR / "openapi_history"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def page(title: str, body: str, active: str = "", prefix: str = "") -> str:
    nav_links = [
        ("首页", f"{prefix or './'}", "home"),
        ("版本列表", f"{prefix}versions/", "versions"),
        ("最新差异", f"{prefix}changelog/", "changelog"),
        ("原始数据", f"{prefix}openapi_history/manifest.json", "data"),
    ]
    nav = []
    for label, href, key in nav_links:
        cls = "active" if key == active else ""
        nav.append(f'<a class="{cls}" href="{href}">{escape(label)}</a>')

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #0b1020;
        --panel: #11182b;
        --panel-2: #0d1426;
        --line: #26324a;
        --text: #e5eefb;
        --muted: #98a7bf;
        --accent: #7dd3fc;
        --green: #86efac;
        --red: #fca5a5;
        --yellow: #fde68a;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        background:
          radial-gradient(circle at top left, rgba(125, 211, 252, 0.12), transparent 36%),
          radial-gradient(circle at top right, rgba(134, 239, 172, 0.08), transparent 30%),
          var(--bg);
        color: var(--text);
      }}
      a {{ color: var(--accent); text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      .wrap {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }}
      .hero, .card {{ background: linear-gradient(180deg, rgba(17,24,43,0.96), rgba(13,20,38,0.96)); border: 1px solid var(--line); border-radius: 18px; }}
      .hero {{ padding: 24px; }}
      .card {{ padding: 20px; margin-top: 16px; }}
      .meta {{ color: var(--muted); font-size: 14px; }}
      .nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
      .nav a {{ padding: 8px 12px; border: 1px solid var(--line); border-radius: 999px; background: rgba(255,255,255,0.03); }}
      .nav a.active {{ background: rgba(125, 211, 252, 0.12); border-color: rgba(125, 211, 252, 0.35); }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 16px; }}
      .stat {{ padding: 14px; border: 1px solid var(--line); border-radius: 14px; background: rgba(255,255,255,0.02); }}
      .stat strong {{ display: block; font-size: 28px; margin-top: 4px; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 10px 8px; vertical-align: top; }}
      th {{ color: var(--muted); font-weight: 600; }}
      code, pre {{ background: var(--panel-2); border-radius: 10px; }}
      pre {{ padding: 14px; overflow: auto; border: 1px solid var(--line); }}
      .badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: rgba(255,255,255,0.05); margin-right: 8px; }}
      .added {{ color: var(--green); }}
      .removed {{ color: var(--red); }}
      .changed {{ color: var(--yellow); }}
      .muted {{ color: var(--muted); }}
      .section-title {{ display: flex; justify-content: space-between; align-items: end; gap: 12px; }}
      .section-title h2, .section-title h3 {{ margin: 0; }}
      .stack {{ display: flex; flex-direction: column; gap: 6px; }}
      .endpoint-list {{ display: grid; gap: 12px; margin-top: 14px; }}
      .endpoint {{ border: 1px solid var(--line); border-radius: 16px; padding: 16px; background: rgba(255,255,255,0.02); }}
      .endpoint-head {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
      .endpoint h3 {{ margin: 12px 0 8px; }}
      .endpoint-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
      .method {{ font-weight: 700; letter-spacing: 0.04em; }}
      .method-get {{ color: var(--green); }}
      .method-post {{ color: #93c5fd; }}
      .method-put {{ color: #fcd34d; }}
      .method-patch {{ color: #fdba74; }}
      .method-delete {{ color: var(--red); }}
      .method-head, .method-options {{ color: var(--muted); }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="hero">
        <div class="meta">GitHub Pages 版本中心</div>
        <h1 style="margin: 10px 0 0;">{escape(title)}</h1>
        <div class="nav">
          {"".join(nav)}
        </div>
      </div>
      {body}
    </div>
  </body>
</html>
"""


def fmt_counts(summary: dict[str, int]) -> str:
    return (
        f'<span class="badge added">新增 {summary.get("added", 0)}</span>'
        f'<span class="badge removed">删除 {summary.get("removed", 0)}</span>'
        f'<span class="badge changed">变更 {summary.get("changed", 0)}</span>'
    )


def collect_endpoints(spec: dict) -> list[dict]:
    endpoints: list[dict] = []
    for http_path, methods in (spec.get("paths") or {}).items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": http_path,
                    "summary": operation.get("summary") or "未命名接口",
                    "description": operation.get("description") or "",
                    "tags": operation.get("tags") or ["default"],
                    "parameters": operation.get("parameters") or [],
                    "responses": list((operation.get("responses") or {}).keys()),
                }
            )
    return sorted(endpoints, key=lambda item: f"{item['method']} {item['path']}")


def render_endpoint_card(endpoint: dict) -> str:
    method = endpoint["method"].lower()
    tag_text = " · ".join(endpoint.get("tags") or [])
    params = endpoint.get("parameters") or []
    resp = endpoint.get("responses") or []
    return f"""
    <div class="endpoint">
      <div class="endpoint-head">
        <span class="method method-{method}">{escape(endpoint["method"])}</span>
        <code>{escape(endpoint["path"])}</code>
      </div>
      <h3>{escape(endpoint["summary"])}</h3>
      <p class="muted">{escape(endpoint["description"])}</p>
      <div class="endpoint-meta">
        <span class="badge">{escape(tag_text)}</span>
        <span class="badge">参数 {len(params)}</span>
        <span class="badge">响应 {len(resp)}</span>
      </div>
    </div>
    """


def render_diff_table(items: list[dict], kind: str) -> str:
    if not items:
        return f'<div class="card"><h3>{escape(kind)}</h3><p class="muted">没有变化。</p></div>'

    rows = []
    for item in items:
        key = item.get("key") or item.get("after", {}).get("key") or item.get("before", {}).get("key")
        summary = item.get("operation", {}).get("summary")
        if not summary:
            summary = item.get("after", {}).get("operation", {}).get("summary") or item.get("before", {}).get("operation", {}).get("summary")
        rows.append(f"<tr><td><code>{escape(key)}</code></td><td>{escape(summary or '')}</td></tr>")

    return f"""
    <div class="card">
      <h3>{escape(kind)}</h3>
      <table>
        <thead><tr><th>接口</th><th>说明</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    """


def render_index(manifest: dict) -> str:
    latest_version = manifest.get("latest")
    latest_entry = None
    for entry in manifest.get("versions", []):
        if entry.get("version") == latest_version:
            latest_entry = entry
            break

    latest_spec = read_json(HISTORY_DIR / "versions" / f"{latest_version}.json") if latest_version else None
    endpoints = collect_endpoints(latest_spec) if latest_spec else []
    tags = sorted({tag for endpoint in endpoints for tag in (endpoint.get("tags") or [])})
    latest_counts = latest_entry.get("summary", {}) if latest_entry else {}
    body = [
        '<div class="card">',
        '<div class="section-title"><h2>最新文档</h2><span class="muted">Scalar 风格静态页</span></div>',
        '<div class="grid">',
        f'<div class="stat"><span class="muted">最新版本</span><strong>{escape(latest_version or "-")}</strong></div>',
        f'<div class="stat"><span class="muted">接口数量</span><strong>{len(endpoints)}</strong></div>',
        f'<div class="stat"><span class="muted">标签数量</span><strong>{len(tags)}</strong></div>',
        f'<div class="stat"><span class="muted">新增</span><strong>{latest_counts.get("added", 0)}</strong></div>',
        f'<div class="stat"><span class="muted">删除</span><strong>{latest_counts.get("removed", 0)}</strong></div>',
        f'<div class="stat"><span class="muted">变更</span><strong>{latest_counts.get("changed", 0)}</strong></div>',
        "</div>",
    ]

    if latest_entry:
        body.extend(
            [
                '<p style="margin-top:16px;">',
                f'<a href="versions/{escape(latest_entry["version"])}/">查看最新版本</a> · ',
                '<a href="changelog/">查看最新差异</a> · ',
                '<a href="openapi_history/manifest.json">查看原始清单</a>',
                "</p>",
            ]
        )
    body.append("</div>")

    if latest_spec:
        body.append('<div class="card"><div class="section-title"><h2>接口参考</h2><span class="muted">按当前最新规范渲染</span></div>')
        current_tag = None
        for endpoint in endpoints:
            first_tag = (endpoint.get("tags") or ["default"])[0]
            if first_tag != current_tag:
                if current_tag is not None:
                    body.append("</div>")
                current_tag = first_tag
                body.append(f'<h3 style="margin-top:18px;">{escape(first_tag)}</h3><div class="endpoint-list">')
            body.append(render_endpoint_card(endpoint))
        if current_tag is not None:
            body.append("</div>")
        body.append("</div>")

    body.append('<div class="card"><h2>版本历史</h2><table><thead><tr><th>版本</th><th>时间</th><th>摘要</th><th>操作</th></tr></thead><tbody>')
    for entry in reversed(manifest.get("versions", [])):
        version = entry["version"]
        created_at = entry["created_at"]
        summary = entry.get("summary", {})
        body.append(
            "<tr>"
            f'<td><code>{escape(version)}</code></td>'
            f"<td class=\"muted\">{escape(created_at)}</td>"
            f"<td>{fmt_counts(summary)}</td>"
            f'<td><a href="versions/{escape(version)}/">查看</a> · <a href="openapi_history/versions/{escape(version)}.json">JSON</a></td>'
            "</tr>"
        )
    body.append("</tbody></table></div>")
    return page("接口版本中心", "".join(body), active="home", prefix="")


def render_versions(manifest: dict) -> str:
    rows = []
    for entry in reversed(manifest.get("versions", [])):
        version = entry["version"]
        rows.append(
            "<tr>"
            f'<td><code>{escape(version)}</code></td>'
            f'<td>{escape(entry["created_at"])}</td>'
            f'<td>{fmt_counts(entry.get("summary", {}))}</td>'
            f'<td><a href="{escape(version)}/">打开</a></td>'
            "</tr>"
        )

    body = f"""
    <div class="card">
      <div class="section-title">
        <h2>版本列表</h2>
        <span class="muted">共 {len(manifest.get("versions", []))} 个版本</span>
      </div>
      <table>
        <thead><tr><th>版本</th><th>创建时间</th><th>摘要</th><th>操作</th></tr></thead>
        <tbody>{''.join(rows) or '<tr><td colspan="4" class="muted">暂无版本。</td></tr>'}</tbody>
      </table>
    </div>
    """
    return page("接口版本列表", body, active="versions", prefix="../")


def render_changelog(manifest: dict) -> str:
    latest_version = manifest.get("latest")
    if not latest_version:
        return page("最新差异", '<div class="card"><p class="muted">暂无版本历史。</p></div>', active="changelog")

    latest_diff = read_json(HISTORY_DIR / "diffs" / f"{latest_version}.json")
    latest_entry = None
    for entry in manifest.get("versions", []):
        if entry.get("version") == latest_version:
            latest_entry = entry
            break

    header = f"""
    <div class="card">
      <h2>最新差异</h2>
      <p class="muted">版本基线：{escape(latest_diff.get("previousVersion"))} → {escape(latest_diff.get("currentVersion"))}</p>
      <p>{fmt_counts(latest_entry.get("summary", {}) if latest_entry else {})}</p>
      <p><a href="../versions/{escape(latest_version)}/">打开版本页</a> · <a href="../openapi_history/diffs/{escape(latest_version)}.json">原始 diff JSON</a></p>
    </div>
    """
    return page(
        "接口差异",
        header + render_diff_table(latest_diff.get("added", []), "新增接口")
        + render_diff_table(latest_diff.get("removed", []), "删除接口")
        + render_diff_table(latest_diff.get("changed", []), "变更接口"),
        active="changelog",
        prefix="../",
    )


def render_version_page(entry: dict) -> str:
    version = entry["version"]
    diff = read_json(HISTORY_DIR / "diffs" / f"{version}.json")
    parent = entry.get("parent_version") or "无"
    body = f"""
    <div class="card">
      <div class="section-title">
        <h2>{escape(version)}</h2>
        <span class="muted">{escape(entry["created_at"])}</span>
      </div>
      <p class="muted">上一个版本：{escape(parent)}</p>
      <p>{fmt_counts(entry.get("summary", {}))}</p>
      <p>
        <a href="../../openapi_history/versions/{escape(version)}.json">规范 JSON</a> ·
        <a href="../../openapi_history/diffs/{escape(version)}.json">差异 JSON</a> ·
        <a href="../">返回版本列表</a>
      </p>
    </div>
    {render_diff_table(diff.get("added", []), "新增接口")}
    {render_diff_table(diff.get("removed", []), "删除接口")}
    {render_diff_table(diff.get("changed", []), "变更接口")}
    """
    return page(f"版本 {version}", body, active="versions", prefix="../../")


def main() -> int:
    if not HISTORY_DIR.exists():
        raise SystemExit(f"missing history directory: {HISTORY_DIR}")

    manifest = read_json(HISTORY_DIR / "manifest.json")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copytree(HISTORY_DIR, OUTPUT_HISTORY_DIR)

    write_text(OUTPUT_DIR / "index.html", render_index(manifest))
    write_text(OUTPUT_DIR / "versions" / "index.html", render_versions(manifest))
    write_text(OUTPUT_DIR / "changelog" / "index.html", render_changelog(manifest))

    for entry in manifest.get("versions", []):
        version_dir = OUTPUT_DIR / "versions" / entry["version"]
        write_text(version_dir / "index.html", render_version_page(entry))

    print(f"generated {len(manifest.get('versions', []))} version pages in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

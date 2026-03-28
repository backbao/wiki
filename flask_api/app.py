from __future__ import annotations

import json
from flask import Response, redirect, render_template_string, request
from flask_cors import CORS
from flask_openapi3 import Info, OpenAPI

from api.chat import chat_bp
from api.image import image_bp
from versioning import (
    ensure_snapshot,
    get_version_entry,
    load_current_spec,
    load_manifest,
    load_version_diff,
    load_version_spec,
)


info = Info(title="AI Chat API", version="1.0.0")
app = OpenAPI(__name__, info=info)
CORS(app)

app.register_api(chat_bp)
app.register_api(image_bp)


def _render_layout(title: str, body: str) -> str:
    return render_template_string(
        """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
      .wrap { max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }
      .card { background: #111827; border: 1px solid #243244; border-radius: 16px; padding: 20px; margin: 16px 0; }
      a { color: #7dd3fc; text-decoration: none; }
      a:hover { text-decoration: underline; }
      code, pre { background: #0b1220; border-radius: 10px; }
      pre { padding: 16px; overflow: auto; }
      table { width: 100%; border-collapse: collapse; margin-top: 12px; }
      th, td { border-bottom: 1px solid #243244; padding: 10px 8px; text-align: left; vertical-align: top; }
      .muted { color: #94a3b8; }
      .badge { display: inline-block; padding: 4px 10px; border-radius: 999px; background: #1e293b; margin-right: 8px; }
      .added { color: #86efac; }
      .removed { color: #fca5a5; }
      .changed { color: #fde68a; }
      h1, h2, h3 { margin-top: 0; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <div class="muted">Flask-OpenAPI3 版本中心</div>
        <h1>{{ title }}</h1>
        <p>
          <a href="/openapi/scalar">Scalar</a>
          <span class="badge"><a href="/openapi/versions">版本列表</a></span>
          <span class="badge"><a href="/openapi/changelog">最新差异</a></span>
          <span class="badge"><a href="/openapi/openapi.json">当前规范 JSON</a></span>
        </p>
      </div>
      {{ body | safe }}
    </div>
  </body>
</html>
        """,
        title=title,
        body=body,
    )


def _render_diff_table(items: list[dict], kind: str) -> str:
    if not items:
        return f'<div class="card"><h2>{kind}</h2><p class="muted">没有变化。</p></div>'

    rows = []
    for item in items:
        key = item.get("key") or item.get("after", {}).get("key") or item.get("before", {}).get("key")
        summary = item.get("operation", {}).get("summary")
        if not summary:
            summary = item.get("after", {}).get("operation", {}).get("summary") or item.get("before", {}).get("operation", {}).get("summary")
        rows.append(f"<tr><td><code>{key}</code></td><td>{summary or ''}</td></tr>")

    return f"""
      <div class="card">
        <h2>{kind}</h2>
        <table>
          <thead><tr><th>接口</th><th>说明</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    """


def _render_version_summary(version_entry: dict, diff: dict | None = None) -> str:
    parent = version_entry.get("parent_version") or "无"
    summary = version_entry.get("summary", {})
    diff_html = ""
    if diff:
        diff_html = f"""
          <div class="card">
            <h2>最新差异</h2>
            <p>
              <span class="badge added">新增 {summary.get('added', 0)}</span>
              <span class="badge removed">删除 {summary.get('removed', 0)}</span>
              <span class="badge changed">变更 {summary.get('changed', 0)}</span>
            </p>
          </div>
          {_render_diff_table(diff.get('added', []), '新增接口')}
          {_render_diff_table(diff.get('removed', []), '删除接口')}
          {_render_diff_table(diff.get('changed', []), '变更接口')}
        """

    return f"""
      <div class="card">
        <h2>{version_entry['version']}</h2>
        <p class="muted">创建时间：{version_entry['created_at']} | 上一个版本：{parent}</p>
        <p>
          <span class="badge added">新增 {summary.get('added', 0)}</span>
          <span class="badge removed">删除 {summary.get('removed', 0)}</span>
          <span class="badge changed">变更 {summary.get('changed', 0)}</span>
        </p>
        <p>
          <a href="/openapi/versions/{version_entry['version']}">查看该版本规范</a>
          <span class="badge"><a href="/openapi/changelog?version={version_entry['version']}">查看该版本差异</a></span>
        </p>
      </div>
      {diff_html}
    """


@app.route("/")
def index():
    return redirect("/openapi/scalar")


@app.route("/openapi/versions")
def versions():
    manifest = load_manifest()
    latest_version = manifest.get("latest")
    latest_entry = get_version_entry(latest_version) if latest_version else None
    latest_diff = load_version_diff(latest_version) if latest_version else None

    version_cards = []
    for entry in reversed(manifest.get("versions", [])):
        version_cards.append(_render_version_summary(entry))

    body = ""
    if latest_entry:
        body += _render_version_summary(latest_entry, latest_diff)
    body += '<div class="card"><h2>历史版本</h2>' + "".join(version_cards) + "</div>"
    return _render_layout("接口版本列表", body)


@app.route("/openapi/changelog")
def changelog():
    manifest = load_manifest()
    version = request.args.get("version")
    if version:
        entry = get_version_entry(version)
    else:
        version = manifest.get("latest")
        entry = get_version_entry(version) if version else None

    if not entry:
        return _render_layout("接口差异", '<div class="card"><p class="muted">暂无版本历史。</p></div>')

    diff = load_version_diff(entry["version"]) or {"added": [], "removed": [], "changed": []}
    body = _render_version_summary(entry, diff)
    return _render_layout("接口差异", body)


@app.route("/openapi/versions/<version>")
def version_spec(version: str):
    spec = load_version_spec(version)
    if spec is None:
        return {"error": "version not found", "version": version}, 404
    return Response(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", mimetype="application/json")


@app.route("/openapi/version/latest")
def latest_version():
    entry = ensure_snapshot(app)
    return entry


@app.route("/openapi/version/current")
def current_version():
    spec = load_current_spec(app)
    return spec.get("info", {})


ensure_snapshot(app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

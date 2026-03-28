from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
HISTORY_DIR = BASE_DIR / "openapi_history"
VERSIONS_DIR = HISTORY_DIR / "versions"
DIFFS_DIR = HISTORY_DIR / "diffs"
MANIFEST_FILE = HISTORY_DIR / "manifest.json"

METHOD_ORDER = ["get", "post", "put", "patch", "delete", "head", "options"]


@dataclass
class VersionEntry:
    version: str
    created_at: str
    spec_hash: str
    parent_version: str | None
    spec_file: str
    diff_file: str | None
    summary: dict[str, int]


def _ensure_dirs() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    DIFFS_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _spec_hash(spec: dict[str, Any]) -> str:
    payload = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_ref(spec: dict[str, Any], ref: str | None) -> dict[str, Any] | None:
    if not ref or not ref.startswith("#/"):
        return None

    node: Any = spec
    for part in ref.removeprefix("#/").split("/"):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return None
    return node if isinstance(node, dict) else None


def _simplify_schema(
    spec: dict[str, Any], schema: dict[str, Any] | None, seen: set[str] | None = None
) -> Any:
    if not schema:
        return None

    seen = seen or set()

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen:
            return {"$ref": ref}
        resolved = _resolve_ref(spec, ref)
        if not resolved:
            return {"$ref": ref}
        seen.add(ref)
        return _simplify_schema(spec, resolved, seen)

    result: dict[str, Any] = {}
    for key in ("type", "title", "description", "default", "example", "format", "nullable", "enum"):
        if key in schema:
            result[key] = schema[key]

    if "required" in schema:
        result["required"] = list(schema["required"])

    if "properties" in schema:
        result["properties"] = {
            name: _simplify_schema(spec, prop, seen.copy()) for name, prop in schema["properties"].items()
        }

    if "items" in schema:
        result["items"] = _simplify_schema(spec, schema["items"], seen.copy())

    for key in ("oneOf", "anyOf", "allOf"):
        if key in schema:
            result[key] = [_simplify_schema(spec, item, seen.copy()) for item in schema[key]]

    return result


def _simplify_operation(spec: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    request_schema = (
        operation.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    responses: dict[str, Any] = {}

    for code, resp in (operation.get("responses") or {}).items():
        if code == "422":
            continue
        responses[code] = {
            "description": resp.get("description", ""),
            "schema": _simplify_schema(
                spec,
                (resp.get("content") or {}).get("application/json", {}).get("schema"),
            ),
        }

    return {
        "summary": operation.get("summary", ""),
        "description": operation.get("description", ""),
        "tags": operation.get("tags", []),
        "parameters": [
            {
                "name": param.get("name"),
                "in": param.get("in"),
                "required": bool(param.get("required")),
                "description": param.get("description", ""),
                "type": (param.get("schema") or {}).get("type", "-"),
            }
            for param in operation.get("parameters", [])
        ],
        "requestBody": _simplify_schema(spec, request_schema) if request_schema else None,
        "responses": responses,
    }


def _flatten_endpoints(spec: dict[str, Any]) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []

    for http_path, methods in (spec.get("paths") or {}).items():
        for method, operation in methods.items():
            if method not in METHOD_ORDER:
                continue
            endpoints.append(
                {
                    "key": f"{method.upper()} {http_path}",
                    "method": method,
                    "path": http_path,
                    "operation": operation,
                    "normalized": _simplify_operation(spec, operation),
                }
            )

    return sorted(endpoints, key=lambda item: item["key"])


def compute_diff(previous_spec: dict[str, Any] | None, current_spec: dict[str, Any]) -> dict[str, Any]:
    if previous_spec is None:
        return {
            "previousVersion": None,
            "currentVersion": current_spec.get("info", {}).get("version", "unknown"),
            "added": [],
            "removed": [],
            "changed": [],
        }

    prev_map = {item["key"]: item for item in _flatten_endpoints(previous_spec)}
    cur_map = {item["key"]: item for item in _flatten_endpoints(current_spec)}

    added = [cur_map[key] for key in sorted(cur_map.keys() - prev_map.keys())]
    removed = [prev_map[key] for key in sorted(prev_map.keys() - cur_map.keys())]
    changed = []

    for key in sorted(prev_map.keys() & cur_map.keys()):
        before = prev_map[key]
        after = cur_map[key]
        if json.dumps(before["normalized"], ensure_ascii=False, sort_keys=True) != json.dumps(
            after["normalized"], ensure_ascii=False, sort_keys=True
        ):
            changed.append({"before": before, "after": after})

    return {
        "previousVersion": previous_spec.get("info", {}).get("version", "unknown"),
        "currentVersion": current_spec.get("info", {}).get("version", "unknown"),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _summary_from_diff(diff: dict[str, Any]) -> dict[str, int]:
    return {
        "added": len(diff["added"]),
        "removed": len(diff["removed"]),
        "changed": len(diff["changed"]),
    }


def load_manifest() -> dict[str, Any]:
    _ensure_dirs()
    manifest = _load_json(MANIFEST_FILE, {"latest": None, "versions": []})
    manifest.setdefault("latest", None)
    manifest.setdefault("versions", [])
    return manifest


def save_manifest(manifest: dict[str, Any]) -> None:
    _ensure_dirs()
    _save_json(MANIFEST_FILE, manifest)


def load_current_spec(app) -> dict[str, Any]:
    response = app.test_client().get("/openapi/openapi.json")
    if response.status_code != 200:
        raise RuntimeError(f"failed to load openapi json: HTTP {response.status_code}")
    return response.get_json()


def ensure_snapshot(app) -> dict[str, Any]:
    _ensure_dirs()
    current_spec = load_current_spec(app)
    current_hash = _spec_hash(current_spec)
    manifest = load_manifest()
    versions: list[dict[str, Any]] = manifest["versions"]
    latest = versions[-1] if versions else None

    if latest and latest["spec_hash"] == current_hash:
        return latest

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    version = f"v{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    while (VERSIONS_DIR / f"{version}.json").exists():
        version = f"{version}_1"

    parent_version = latest["version"] if latest else None
    previous_spec = None
    if latest:
        previous_spec = _load_json(VERSIONS_DIR / f"{latest['version']}.json", None)

    diff = compute_diff(previous_spec, current_spec)
    summary = _summary_from_diff(diff)
    spec_file = VERSIONS_DIR / f"{version}.json"
    diff_file = DIFFS_DIR / f"{version}.json"

    _save_json(spec_file, current_spec)
    _save_json(diff_file, diff)

    entry = VersionEntry(
        version=version,
        created_at=created_at,
        spec_hash=current_hash,
        parent_version=parent_version,
        spec_file=spec_file.relative_to(HISTORY_DIR).as_posix(),
        diff_file=diff_file.relative_to(HISTORY_DIR).as_posix(),
        summary=summary,
    )
    versions.append(asdict(entry))
    manifest["latest"] = version
    manifest["versions"] = versions
    save_manifest(manifest)
    return asdict(entry)


def get_version_entry(version: str) -> dict[str, Any] | None:
    manifest = load_manifest()
    for entry in manifest["versions"]:
        if entry["version"] == version:
            return entry
    return None


def load_version_spec(version: str) -> dict[str, Any] | None:
    path = VERSIONS_DIR / f"{version}.json"
    if not path.exists():
        return None
    return _load_json(path, None)


def load_version_diff(version: str) -> dict[str, Any] | None:
    path = DIFFS_DIR / f"{version}.json"
    if not path.exists():
        return None
    return _load_json(path, None)

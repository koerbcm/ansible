#!/usr/bin/env python3
"""Socket.IO-backed Uptime Kuma automation helpers for Ansible.

This script replaces REST-wrapper calls with direct Uptime Kuma Socket.IO calls
via the `uptime-kuma-api` / `uptime-kuma-api-v2` client library.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

try:
    from uptime_kuma_api import UptimeKumaApi
except ImportError as exc:  # pragma: no cover - runtime environment concern
    print(
        json.dumps(
            {
                "ok": False,
                "error": (
                    "Missing dependency 'uptime_kuma_api'. Install one of:\n"
                    "  pip install uptime-kuma-api-v2\n"
                    "  pip install uptime-kuma-api"
                ),
                "details": str(exc),
            }
        ),
        file=sys.stderr,
    )
    sys.exit(2)


def _as_list(value: Any, key: str | None = None) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if key and isinstance(value, dict):
        nested = value.get(key)
        if isinstance(nested, list):
            return nested
    return []


def _expected_leaf_name(path_name: str) -> str:
    if " / " not in path_name:
        return path_name.strip()
    return path_name.split(" / ", 1)[1].strip()


def _normalize_leaf_for_lookup(value: str) -> str:
    leaf = str(value).strip()
    for suffix in (" - Internal", " - External"):
        if leaf.endswith(suffix):
            leaf = leaf[: -len(suffix)].strip()
    return leaf


def _split_group_and_leaf(path_name: str) -> tuple[str, str]:
    text = str(path_name).strip()
    if " / " not in text:
        return text, text
    group, leaf = text.split(" / ", 1)
    return group.strip(), leaf.strip()


def _normalize_path_for_lookup(path_name: str) -> str:
    path_name = str(path_name).strip()
    if " / " not in path_name:
        return _normalize_leaf_for_lookup(path_name)
    group, rest = path_name.split(" / ", 1)
    group = group.strip()
    rest = rest.strip()
    repeated_prefix = f"{group} / "
    while rest.startswith(repeated_prefix):
        rest = rest[len(repeated_prefix) :]
    return f"{group} / {_normalize_leaf_for_lookup(rest)}".strip()


def _find_monitor_for_expected(
    snapshot: Dict[str, Any], expected_path_name: str, required_tags: List[str]
) -> Dict[str, Any] | None:
    expected_key = _normalize_path_for_lookup(expected_path_name)
    direct = snapshot["monitor_by_normalized_path"].get(expected_key)
    if direct:
        return direct

    if " / " not in expected_path_name:
        return None

    expected_group, expected_leaf = _split_group_and_leaf(expected_path_name)
    expected_leaf_key = _normalize_leaf_for_lookup(expected_leaf)
    required_tag_set = set(required_tags)

    candidates: List[tuple[int, int, int, Dict[str, Any]]] = []
    for monitor in snapshot["monitors"]:
        normalized_actual_path = _normalize_path_for_lookup(monitor["pathName"])
        if " / " not in normalized_actual_path:
            continue
        actual_group, actual_leaf = _split_group_and_leaf(normalized_actual_path)
        if _normalize_leaf_for_lookup(actual_leaf) != expected_leaf_key:
            continue
        actual_tag_set = {tag["name"] for tag in monitor.get("tags", [])}
        score_group_match = 1 if actual_group == expected_group else 0
        score_tag_overlap = len(required_tag_set & actual_tag_set)
        score_is_non_group = 1 if monitor.get("type") != "group" else 0
        candidates.append((score_group_match, score_tag_overlap, score_is_non_group, monitor))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    if len(candidates) > 1 and candidates[0][:3] == candidates[1][:3]:
        return None
    return candidates[0][3]


def _normalize_tags(raw_tags: Any) -> List[Dict[str, Any]]:
    tags = _as_list(raw_tags, key="tags")
    normalized: List[Dict[str, Any]] = []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        name = str(tag.get("name", "")).strip()
        if not name:
            continue
        normalized.append(
            {
                "id": tag.get("id"),
                "name": name,
                "color": tag.get("color"),
            }
        )
    return normalized


def _normalize_monitor_tags(raw_tags: Any) -> List[Dict[str, Any]]:
    tags = _as_list(raw_tags)
    normalized: List[Dict[str, Any]] = []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        name = str(tag.get("name", "")).strip()
        if not name:
            continue
        normalized.append(
            {
                "id": tag.get("id"),
                "name": name,
                "color": tag.get("color"),
            }
        )
    return normalized


def _normalize_url_for_compare(value: Any) -> str:
    text = str(value or "").strip()
    return text.rstrip("/")


def _normalize_port_for_compare(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_monitors(raw_monitors: Any) -> List[Dict[str, Any]]:
    monitors = _as_list(raw_monitors, key="monitors")
    normalized: List[Dict[str, Any]] = []
    for monitor in monitors:
        if not isinstance(monitor, dict):
            continue
        path_name = monitor.get("pathName") or monitor.get("name")
        if not path_name:
            continue
        parent_raw = monitor.get("parent")
        parent_id = None
        if isinstance(parent_raw, dict):
            parent_id = parent_raw.get("id")
        elif parent_raw is not None:
            parent_id = parent_raw
        normalized.append(
            {
                "id": monitor.get("id"),
                "name": monitor.get("name"),
                "pathName": str(path_name),
                "type": monitor.get("type"),
                "url": monitor.get("url"),
                "hostname": monitor.get("hostname"),
                "port": monitor.get("port"),
                "parent": parent_id,
                "tags": _normalize_monitor_tags(monitor.get("tags")),
            }
        )
    return normalized


def _normalize_maintenances(raw_maintenances: Any) -> List[Dict[str, Any]]:
    maintenances = _as_list(raw_maintenances, key="maintenances")
    normalized: List[Dict[str, Any]] = []
    for maintenance in maintenances:
        if not isinstance(maintenance, dict):
            continue
        title = str(maintenance.get("title", "")).strip()
        if not title:
            continue
        normalized.append(
            {
                "id": maintenance.get("id"),
                "title": title,
            }
        )
    return normalized


def _collect_snapshot(api: Any) -> Dict[str, Any]:
    tags = _normalize_tags(api.get_tags())
    monitors = _normalize_monitors(api.get_monitors())
    maintenances = _normalize_maintenances(api.get_maintenances())

    monitor_by_path: Dict[str, Dict[str, Any]] = {m["pathName"]: m for m in monitors}
    monitor_by_normalized_path: Dict[str, Dict[str, Any]] = {}
    for monitor in monitors:
        normalized_path = _normalize_path_for_lookup(monitor["pathName"])
        monitor_by_normalized_path.setdefault(normalized_path, monitor)
    monitor_path_by_id: Dict[str, str] = {
        str(m.get("id")): _normalize_path_for_lookup(m["pathName"])
        for m in monitors
        if m.get("id") is not None
    }
    tag_id_by_name: Dict[str, Any] = {
        t["name"]: t.get("id")
        for t in tags
        if t.get("id") is not None
    }
    maintenance_by_title: Dict[str, Dict[str, Any]] = {m["title"]: m for m in maintenances}

    maintenance_assignments_by_title: Dict[str, List[str]] = {}
    for maintenance in maintenances:
        maintenance_id = maintenance.get("id")
        title = maintenance["title"]
        if maintenance_id is None:
            maintenance_assignments_by_title[title] = []
            continue

        raw_assignments = _as_list(api.get_monitor_maintenance(int(maintenance_id)))
        assignment_paths: List[str] = []
        for item in raw_assignments:
            if not isinstance(item, dict):
                continue
            monitor_id = item.get("id")
            if monitor_id is None:
                continue
            path = monitor_path_by_id.get(str(monitor_id))
            if path:
                assignment_paths.append(path)
        maintenance_assignments_by_title[title] = sorted(set(assignment_paths))

    return {
        "tags": tags,
        "monitors": monitors,
        "maintenances": maintenances,
        "monitor_by_path": monitor_by_path,
        "monitor_by_normalized_path": monitor_by_normalized_path,
        "tag_id_by_name": tag_id_by_name,
        "maintenance_by_title": maintenance_by_title,
        "maintenance_assignments_by_title": maintenance_assignments_by_title,
    }


def _resolve_monitor_from_gap(
    snapshot: Dict[str, Any], path_name: str, gap: Dict[str, Any]
) -> Dict[str, Any] | None:
    monitor_id = gap.get("actual_monitor_id")
    if monitor_id is not None:
        for monitor in snapshot["monitors"]:
            if monitor.get("id") == monitor_id:
                return monitor
    return snapshot["monitor_by_normalized_path"].get(_normalize_path_for_lookup(path_name))


def _expected_parent_group_path(path_name: str) -> str | None:
    if " / " not in path_name:
        return None
    prefix = path_name.split(" / ", 1)[0].strip()
    return prefix or None


def _compute_state(snapshot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    expected_tags = list(cfg.get("expected_tags", []))
    expected_monitors = list(cfg.get("expected_monitors", []))
    expected_maintenance_scopes = list(cfg.get("expected_maintenance_scopes", []))
    check_unexpected = bool(cfg.get("check_unexpected_monitors", True))

    actual_tag_names = sorted({tag["name"] for tag in snapshot["tags"]})
    actual_monitor_path_names = sorted(set(snapshot["monitor_by_normalized_path"].keys()))
    actual_maintenance_titles = sorted({maintenance["title"] for maintenance in snapshot["maintenances"]})

    expected_monitor_path_names = sorted(
        {
            str(item.get("path_name", "")).strip()
            for item in expected_monitors
            if str(item.get("path_name", "")).strip()
        }
    )

    missing_expected_tags = sorted(set(expected_tags) - set(actual_tag_names))

    untagged_non_group_monitors = sorted(
        monitor["pathName"]
        for monitor in snapshot["monitors"]
        if monitor.get("type") != "group" and len(monitor.get("tags", [])) == 0
    )

    matched_expected_monitor_paths: List[str] = []
    matched_actual_monitor_paths: List[str] = []

    monitor_tag_gaps: List[Dict[str, Any]] = []
    parent_group_gaps: List[Dict[str, Any]] = []
    monitor_name_gaps: List[Dict[str, Any]] = []
    monitor_target_gaps: List[Dict[str, Any]] = []
    for expected in expected_monitors:
        path_name = str(expected.get("path_name", "")).strip()
        if not path_name:
            continue
        required_tags = list(expected.get("required_tags", []))
        actual_monitor = _find_monitor_for_expected(snapshot, path_name, required_tags)
        if actual_monitor:
            matched_expected_monitor_paths.append(_normalize_path_for_lookup(path_name))
            matched_actual_monitor_paths.append(_normalize_path_for_lookup(actual_monitor["pathName"]))
        expected_parent_group_path = _expected_parent_group_path(path_name)
        if actual_monitor and expected_parent_group_path:
            expected_parent = snapshot["monitor_by_normalized_path"].get(
                _normalize_path_for_lookup(expected_parent_group_path)
            )
            expected_parent_id = expected_parent.get("id") if expected_parent else None
            actual_parent_id = actual_monitor.get("parent")
            if expected_parent_id is not None and actual_parent_id != expected_parent_id:
                parent_group_gaps.append(
                    {
                        "path_name": path_name,
                        "actual_monitor_id": actual_monitor.get("id"),
                        "actual_monitor_path_name": actual_monitor.get("pathName"),
                        "expected_parent_path_name": expected_parent_group_path,
                        "expected_parent_id": expected_parent_id,
                        "actual_parent_id": actual_parent_id,
                    }
                )

        if actual_monitor:
            expected_name = _expected_leaf_name(path_name)
            actual_name = str(actual_monitor.get("name", "")).strip()
            if expected_name and actual_name and actual_name != expected_name:
                monitor_name_gaps.append(
                    {
                        "path_name": path_name,
                        "actual_monitor_id": actual_monitor.get("id"),
                        "actual_monitor_path_name": actual_monitor.get("pathName"),
                        "expected_name": expected_name,
                        "actual_name": actual_name,
                    }
                )

        if not required_tags:
            pass
        elif actual_monitor:
            actual_tags = sorted(tag["name"] for tag in actual_monitor.get("tags", []))
            missing_tags = sorted(set(required_tags) - set(actual_tags))
            if missing_tags:
                monitor_tag_gaps.append(
                    {
                        "path_name": path_name,
                        "actual_monitor_id": actual_monitor.get("id"),
                        "actual_monitor_path_name": actual_monitor.get("pathName"),
                        "required_tags": required_tags,
                        "missing_tags": missing_tags,
                        "actual_tags": actual_tags,
                    }
                )

        create_payload = expected.get("create_payload")
        if not isinstance(create_payload, dict) or not actual_monitor:
            continue

        expected_target: Dict[str, Any] = {}
        actual_target: Dict[str, Any] = {}
        mismatches: List[Dict[str, Any]] = []

        if "type" in create_payload:
            expected_type = create_payload.get("type")
            actual_type = actual_monitor.get("type")
            expected_target["type"] = expected_type
            actual_target["type"] = actual_type
            if expected_type != actual_type:
                mismatches.append(
                    {
                        "field": "type",
                        "expected": expected_type,
                        "actual": actual_type,
                    }
                )

        if "url" in create_payload:
            expected_url = _normalize_url_for_compare(create_payload.get("url"))
            actual_url = _normalize_url_for_compare(actual_monitor.get("url"))
            expected_target["url"] = create_payload.get("url")
            actual_target["url"] = actual_monitor.get("url")
            if expected_url != actual_url:
                mismatches.append(
                    {
                        "field": "url",
                        "expected": create_payload.get("url"),
                        "actual": actual_monitor.get("url"),
                    }
                )

        if "hostname" in create_payload:
            expected_hostname = str(create_payload.get("hostname", "")).strip()
            actual_hostname = str(actual_monitor.get("hostname", "")).strip()
            expected_target["hostname"] = create_payload.get("hostname")
            actual_target["hostname"] = actual_monitor.get("hostname")
            if expected_hostname != actual_hostname:
                mismatches.append(
                    {
                        "field": "hostname",
                        "expected": create_payload.get("hostname"),
                        "actual": actual_monitor.get("hostname"),
                    }
                )

        if "port" in create_payload:
            expected_port = _normalize_port_for_compare(create_payload.get("port"))
            actual_port = _normalize_port_for_compare(actual_monitor.get("port"))
            expected_target["port"] = create_payload.get("port")
            actual_target["port"] = actual_monitor.get("port")
            if expected_port != actual_port:
                mismatches.append(
                    {
                        "field": "port",
                        "expected": create_payload.get("port"),
                        "actual": actual_monitor.get("port"),
                    }
                )

        if mismatches:
            monitor_target_gaps.append(
                {
                    "path_name": path_name,
                    "actual_monitor_id": actual_monitor.get("id"),
                    "actual_monitor_path_name": actual_monitor.get("pathName"),
                    "expected_target": expected_target,
                    "actual_target": actual_target,
                    "mismatches": mismatches,
                }
            )

    missing_expected_monitors = sorted(
        set(expected_monitor_path_names) - set(matched_expected_monitor_paths)
    )
    unexpected_monitors = (
        sorted(set(actual_monitor_path_names) - set(matched_actual_monitor_paths))
        if check_unexpected
        else []
    )

    expected_maintenance_titles = [str(item.get("title", "")).strip() for item in expected_maintenance_scopes]
    expected_maintenance_titles = sorted([title for title in expected_maintenance_titles if title])

    missing_expected_maintenances = sorted(set(expected_maintenance_titles) - set(actual_maintenance_titles))

    maintenance_scope_gaps: List[Dict[str, Any]] = []
    assignments = snapshot["maintenance_assignments_by_title"]
    for scope in expected_maintenance_scopes:
        title = str(scope.get("title", "")).strip()
        if not title or title not in assignments:
            continue
        expected_paths = sorted(set(scope.get("expected_monitor_path_names", [])))
        assigned_paths = sorted(set(assignments.get(title, [])))
        missing_paths = sorted(set(expected_paths) - set(assigned_paths))
        if missing_paths:
            maintenance_scope_gaps.append(
                {
                    "title": title,
                    "expected_monitor_path_names": expected_paths,
                    "missing_monitor_path_names": missing_paths,
                    "assigned_monitor_path_names": assigned_paths,
                }
            )

    return {
        "expected_tags_count": len(expected_tags),
        "expected_monitors_count": len(expected_monitor_path_names),
        "expected_maintenance_scopes_count": len(expected_maintenance_scopes),
        "missing_expected_tags": missing_expected_tags,
        "missing_expected_monitors": missing_expected_monitors,
        "unexpected_monitors": unexpected_monitors,
        "monitor_tag_gaps": monitor_tag_gaps,
        "parent_group_gaps": parent_group_gaps,
        "monitor_name_gaps": monitor_name_gaps,
        "monitor_target_gaps": monitor_target_gaps,
        "missing_expected_maintenances": missing_expected_maintenances,
        "maintenance_scope_gaps": maintenance_scope_gaps,
        "untagged_non_group_monitors": untagged_non_group_monitors,
    }


def _apply_changes(api: Any, cfg: Dict[str, Any], snapshot: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    apply_mode = bool(cfg.get("apply_mode", False))
    if not apply_mode:
        return {
            "apply_mode": False,
            "apply_changed": False,
            "apply_api_errors": [],
            "created_tags_count": 0,
            "applied_monitor_tags_count": 0,
            "applied_monitor_parent_count": 0,
            "renamed_monitors_count": 0,
            "applied_monitor_target_count": 0,
            "maintenance_scope_attachments_count": 0,
            "created_monitors_count": 0,
            "deleted_unexpected_monitors_count": 0,
        }

    apply_errors: List[Dict[str, Any]] = []
    apply_changed = False
    created_tags_count = 0
    applied_monitor_tags_count = 0
    applied_monitor_parent_count = 0
    renamed_monitors_count = 0
    applied_monitor_target_count = 0
    maintenance_scope_attachments_count = 0
    created_monitors_count = 0
    deleted_unexpected_monitors_count = 0

    tag_colors = dict(cfg.get("tag_colors", {}))
    default_tag_color = str(cfg.get("default_tag_color", "#D97706"))

    if bool(cfg.get("apply_create_missing_tags", True)):
        for tag_name in state["missing_expected_tags"]:
            try:
                api.add_tag(name=tag_name, color=tag_colors.get(tag_name, default_tag_color))
                created_tags_count += 1
                apply_changed = True
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "create_tag",
                        "tag_name": tag_name,
                        "error": str(exc),
                    }
                )

    if bool(cfg.get("apply_create_missing_monitors", False)):
        missing_set = set(state["missing_expected_monitors"])
        for expected in cfg.get("expected_monitors", []):
            path_name = str(expected.get("path_name", "")).strip()
            if not path_name or path_name not in missing_set:
                continue
            payload = expected.get("create_payload")
            if isinstance(payload, dict):
                create_payload = dict(payload)
            elif " / " not in path_name:
                # Allow apply mode to create missing top-level groups
                # even when no explicit create_payload is defined.
                create_payload = {"type": "group", "name": path_name}
            else:
                continue
            create_payload.setdefault("name", path_name.split(" / ")[-1])
            expected_parent_group_path = _expected_parent_group_path(path_name)
            if expected_parent_group_path and "parent" not in create_payload:
                parent_monitor = snapshot["monitor_by_normalized_path"].get(
                    _normalize_path_for_lookup(expected_parent_group_path)
                )
                if parent_monitor and parent_monitor.get("id") is not None:
                    create_payload["parent"] = parent_monitor["id"]
            try:
                api.add_monitor(**create_payload)
                created_monitors_count += 1
                apply_changed = True
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "create_monitor",
                        "path_name": path_name,
                        "error": str(exc),
                    }
                )

    if (
        bool(cfg.get("apply_add_missing_required_tags", True))
        or bool(cfg.get("apply_enforce_parent_groups", True))
        or bool(cfg.get("apply_enforce_monitor_names", True))
        or bool(cfg.get("apply_enforce_monitor_targets", True))
        or bool(cfg.get("apply_enforce_maintenance_scope", True))
    ):
        snapshot = _collect_snapshot(api)
        state = _compute_state(snapshot, cfg)

    if bool(cfg.get("apply_add_missing_required_tags", True)):
        for gap in state["monitor_tag_gaps"]:
            path_name = gap["path_name"]
            monitor = _resolve_monitor_from_gap(snapshot, path_name, gap)
            monitor_id = monitor.get("id") if monitor else None
            if monitor_id is None:
                apply_errors.append(
                    {
                        "operation": "add_monitor_tag",
                        "path_name": path_name,
                        "error": "monitor_not_found",
                    }
                )
                continue

            for tag_name in gap["missing_tags"]:
                tag_id = snapshot["tag_id_by_name"].get(tag_name)
                if tag_id is None:
                    apply_errors.append(
                        {
                            "operation": "add_monitor_tag",
                            "path_name": path_name,
                            "tag_name": tag_name,
                            "error": "tag_not_found",
                        }
                    )
                    continue
                try:
                    api.add_monitor_tag(tag_id=tag_id, monitor_id=monitor_id, value="")
                    applied_monitor_tags_count += 1
                    apply_changed = True
                except Exception as exc:  # pylint: disable=broad-except
                    apply_errors.append(
                        {
                            "operation": "add_monitor_tag",
                            "path_name": path_name,
                            "tag_name": tag_name,
                            "error": str(exc),
                        }
                    )

    if bool(cfg.get("apply_enforce_parent_groups", True)):
        for gap in state["parent_group_gaps"]:
            path_name = gap["path_name"]
            expected_parent_id = gap["expected_parent_id"]
            monitor = _resolve_monitor_from_gap(snapshot, path_name, gap)
            monitor_id = monitor.get("id") if monitor else None
            if monitor_id is None:
                apply_errors.append(
                    {
                        "operation": "set_monitor_parent",
                        "path_name": path_name,
                        "error": "monitor_not_found",
                    }
                )
                continue
            try:
                api.edit_monitor(int(monitor_id), parent=int(expected_parent_id))
                applied_monitor_parent_count += 1
                apply_changed = True
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "set_monitor_parent",
                        "path_name": path_name,
                        "expected_parent_id": expected_parent_id,
                        "error": str(exc),
                    }
                )

    if bool(cfg.get("apply_enforce_monitor_names", True)):
        for gap in state["monitor_name_gaps"]:
            path_name = gap["path_name"]
            expected_name = gap["expected_name"]
            monitor = _resolve_monitor_from_gap(snapshot, path_name, gap)
            monitor_id = monitor.get("id") if monitor else None
            if monitor_id is None:
                apply_errors.append(
                    {
                        "operation": "rename_monitor",
                        "path_name": path_name,
                        "error": "monitor_not_found",
                    }
                )
                continue
            try:
                api.edit_monitor(
                    int(monitor_id),
                    name=expected_name,
                )
                renamed_monitors_count += 1
                apply_changed = True
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "rename_monitor",
                        "path_name": path_name,
                        "expected_name": expected_name,
                        "error": str(exc),
                    }
                )

    if bool(cfg.get("apply_enforce_monitor_targets", True)):
        for gap in state["monitor_target_gaps"]:
            path_name = gap["path_name"]
            monitor = _resolve_monitor_from_gap(snapshot, path_name, gap)
            monitor_id = monitor.get("id") if monitor else None
            if monitor_id is None:
                apply_errors.append(
                    {
                        "operation": "set_monitor_target",
                        "path_name": path_name,
                        "error": "monitor_not_found",
                    }
                )
                continue

            expected_target = dict(gap.get("expected_target", {}))
            edit_payload: Dict[str, Any] = {}
            for field in ("type", "url", "hostname", "port"):
                if field in expected_target and expected_target.get(field) is not None:
                    edit_payload[field] = expected_target[field]
            if not edit_payload:
                continue

            try:
                api.edit_monitor(int(monitor_id), **edit_payload)
                applied_monitor_target_count += 1
                apply_changed = True
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "set_monitor_target",
                        "path_name": path_name,
                        "target": edit_payload,
                        "error": str(exc),
                    }
                )

    if bool(cfg.get("apply_enforce_maintenance_scope", True)):
        for gap in state["maintenance_scope_gaps"]:
            title = gap["title"]
            maintenance = snapshot["maintenance_by_title"].get(title)
            maintenance_id = maintenance.get("id") if maintenance else None
            if maintenance_id is None:
                apply_errors.append(
                    {
                        "operation": "attach_monitor_maintenance",
                        "title": title,
                        "error": "maintenance_not_found",
                    }
                )
                continue

            desired_monitor_ids: List[int] = []
            missing_path_names: List[str] = []
            for path_name in gap["expected_monitor_path_names"]:
                monitor = snapshot["monitor_by_normalized_path"].get(_normalize_path_for_lookup(path_name))
                if monitor is None:
                    # Handle eventual consistency after creating groups/monitors
                    # earlier in the same apply run.
                    snapshot = _collect_snapshot(api)
                    monitor = snapshot["monitor_by_normalized_path"].get(
                        _normalize_path_for_lookup(path_name)
                    )
                monitor_id = monitor.get("id") if monitor else None
                if monitor_id is None:
                    missing_path_names.append(path_name)
                    continue
                desired_monitor_ids.append(int(monitor_id))

            if missing_path_names:
                for path_name in missing_path_names:
                    apply_errors.append(
                        {
                            "operation": "attach_monitor_maintenance",
                            "title": title,
                            "path_name": path_name,
                            "error": "monitor_not_found",
                        }
                    )
                continue

            try:
                api.add_monitor_maintenance(
                    int(maintenance_id),
                    [{"id": monitor_id} for monitor_id in sorted(set(desired_monitor_ids))],
                )
                maintenance_scope_attachments_count += len(gap["missing_monitor_path_names"])
                apply_changed = True
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "attach_monitor_maintenance",
                        "title": title,
                        "path_name": ",".join(gap["expected_monitor_path_names"]),
                        "error": str(exc),
                    }
                )

    if bool(cfg.get("apply_delete_unexpected_monitors", False)):
        # Delete deepest paths first so children are removed before parent groups.
        unexpected_paths = sorted(
            state["unexpected_monitors"],
            key=lambda item: item.count(" / "),
            reverse=True,
        )
        for path_name in unexpected_paths:
            monitor = snapshot["monitor_by_normalized_path"].get(_normalize_path_for_lookup(path_name))
            if monitor is None:
                snapshot = _collect_snapshot(api)
                monitor = snapshot["monitor_by_normalized_path"].get(_normalize_path_for_lookup(path_name))
            monitor_id = monitor.get("id") if monitor else None
            if monitor_id is None:
                apply_errors.append(
                    {
                        "operation": "delete_unexpected_monitor",
                        "path_name": path_name,
                        "error": "monitor_not_found",
                    }
                )
                continue
            try:
                api.delete_monitor(int(monitor_id))
                deleted_unexpected_monitors_count += 1
                apply_changed = True
                snapshot = _collect_snapshot(api)
                state = _compute_state(snapshot, cfg)
            except Exception as exc:  # pylint: disable=broad-except
                apply_errors.append(
                    {
                        "operation": "delete_unexpected_monitor",
                        "path_name": path_name,
                        "error": str(exc),
                    }
                )

    return {
        "apply_mode": True,
        "apply_changed": apply_changed,
        "apply_api_errors": apply_errors,
        "created_tags_count": created_tags_count,
        "applied_monitor_tags_count": applied_monitor_tags_count,
        "applied_monitor_parent_count": applied_monitor_parent_count,
        "renamed_monitors_count": renamed_monitors_count,
        "applied_monitor_target_count": applied_monitor_target_count,
        "maintenance_scope_attachments_count": maintenance_scope_attachments_count,
        "created_monitors_count": created_monitors_count,
        "deleted_unexpected_monitors_count": deleted_unexpected_monitors_count,
    }


def _command_maintenance(args: argparse.Namespace) -> int:
    with UptimeKumaApi(args.server_url) as api:
        api.login(args.username, args.password)
        if args.state == "start":
            result = api.resume_maintenance(int(args.maintenance_id))
        else:
            result = api.pause_maintenance(int(args.maintenance_id))
    print(json.dumps({"ok": True, "state": args.state, "result": result}))
    return 0


def _command_audit(_args: argparse.Namespace) -> int:
    cfg = json.load(sys.stdin)

    with UptimeKumaApi(cfg["server_url"]) as api:
        api.login(cfg["username"], cfg["password"])

        snapshot = _collect_snapshot(api)
        state = _compute_state(snapshot, cfg)
        apply = _apply_changes(api, cfg, snapshot, state)

        if apply["apply_mode"] and apply["apply_changed"] and bool(cfg.get("apply_recheck_after_changes", True)):
            snapshot = _collect_snapshot(api)
            state = _compute_state(snapshot, cfg)

    result = {}
    result.update(state)
    result.update(apply)

    print(json.dumps({"ok": True, "result": result}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Uptime Kuma Socket automation helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    maintenance_parser = subparsers.add_parser("maintenance", help="Start/end maintenance window")
    maintenance_parser.add_argument("--server-url", required=True)
    maintenance_parser.add_argument("--username", required=True)
    maintenance_parser.add_argument("--password", required=True)
    maintenance_parser.add_argument("--maintenance-id", required=True)
    maintenance_parser.add_argument("--state", choices=["start", "end"], required=True)

    subparsers.add_parser("audit", help="Run monitor taxonomy audit from stdin JSON config")

    args = parser.parse_args()
    try:
        if args.command == "maintenance":
            return _command_maintenance(args)
        return _command_audit(args)
    except Exception as exc:  # pylint: disable=broad-except
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "error_repr": repr(exc),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

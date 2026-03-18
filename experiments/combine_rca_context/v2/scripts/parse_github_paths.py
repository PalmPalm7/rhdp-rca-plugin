#!/usr/bin/env python3
"""Parse GitHub paths from job context."""

import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_job_name(job_name: str, guid: str) -> dict[str, Any]:
    """Parse RHPDS job name using GUID as anchor. Pattern: {platform}.{catalog}.{env}-{guid}-{action}."""
    warnings = []
    name = job_name.removeprefix("RHPDS ").strip()

    if " " in name:
        name, uuid_suffix = name.split(maxsplit=1)
        warnings.append(f"Removed UUID suffix: {uuid_suffix}")

    guid_pattern = f"-{guid}-"
    if guid_pattern not in name:
        warnings.append(f"GUID '{guid}' not found in job_name")
        return {k: "" for k in ["platform", "catalog_item", "env", "action"]} | {
            "guid": guid,
            "warnings": warnings,
        }

    before_guid, after_guid = name.split(guid_pattern, 1)

    # Parse platform.catalog.env
    parts = before_guid.split(".")
    if len(parts) >= 3:
        platform, env, catalog = parts[0], parts[-1], ".".join(parts[1:-1])
    elif len(parts) == 2:
        platform, catalog, env = parts[0], parts[1], ""
        warnings.append("No env in job_name")
    else:
        platform, catalog, env = parts[0] if parts else "", "", ""
        warnings.append("Could not parse platform.catalog.env")

    # Parse action
    action = ""
    for word in ["provision", "destroy", "stop", "start", "status"]:
        if after_guid.startswith(word):
            action = word
            if len(after_guid) > len(word):
                warnings.append(f"Stripped action suffix: {after_guid[len(word) :]}")
            break

    if not action:
        warnings.append(f"Could not identify action from: {after_guid}")
        action = after_guid

    return {
        "platform": platform,
        "catalog_item": catalog,
        "env": env,
        "guid": guid,
        "action": action,
        "warnings": warnings,
    }


def parse_task_path(task_path: str) -> dict[str, Any]:
    """Parse task_path to extract repository and file location."""
    # Collections pattern
    if match := re.match(
        r"/home/runner/\.ansible/collections/ansible_collections/([^/]+)/([^/]+)/(.+):(\d+)",
        task_path,
    ):
        return {
            "owner": match[1],
            "repo": match[2],
            "file_path": match[3],
            "line_number": int(match[4]),
        }

    # Project pattern
    if match := re.match(r"/runner/project/(.+):(\d+)", task_path):
        return {
            "owner": "redhat-cop",
            "repo": "agnosticd",
            "file_path": match[1],
            "line_number": int(match[2]),
        }

    # Unknown pattern
    parts = task_path.rsplit(":", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return {"owner": "", "repo": "", "file_path": parts[0], "line_number": int(parts[1])}

    return {"owner": "", "repo": "", "file_path": task_path, "line_number": 0}


def build_config_entry(
    order: int, paths: list[str] | str, purpose: str, **kwargs
) -> dict[str, Any]:
    """Build standard config hierarchy entry with path(s) and metadata."""
    entry = {
        "order": order,
        "owner": "rhpds",
        "repo": "agnosticv",
        "purpose": purpose,
    }

    if isinstance(paths, list):
        entry["paths_to_try"] = paths
        entry["fetch_method"] = "try_variations"
    else:
        entry["path"] = paths
        entry["fetch_method"] = "direct"

    entry.update(kwargs)
    return entry


def build_agnosticv_hierarchy(platform: str, catalog: str, env: str) -> list[dict[str, Any]]:
    """Build AgnosticV configuration hierarchy with path variations."""
    hierarchy = [build_config_entry(1, "common.yaml", "base_defaults")]
    platform_norm = platform.replace("-", "_") if platform else ""

    if platform:
        hierarchy.append(
            build_config_entry(
                2,
                [f"{platform_norm}/account.yaml", f"{platform}/account.yaml"],
                "platform_config",
                check_for=["includes/secrets", "!vault"],
                note="Try underscore variant first",
            )
        )

    if platform and catalog and env:
        paths = [
            f"{platform_norm}/{catalog}/{env}.yaml",
            f"{platform_norm}/{catalog}/common.yaml",
        ]
        if platform != platform_norm:
            paths.append(f"{platform}/{catalog}/{env}.yaml")

        hierarchy.append(
            build_config_entry(
                3, paths, "env_overrides", note="Try env.yaml first, fallback to common.yaml"
            )
        )

    return hierarchy


def build_workload_paths(
    owner: str, repo: str, file_path: str, line_number: int
) -> list[dict[str, Any]]:
    """Build workload investigation paths."""
    paths = []

    # Extract role from path
    role_match = re.search(r"roles/([^/]+)/", file_path)
    role = role_match.group(1) if role_match else None

    if role:
        paths.append(
            {
                "owner": owner,
                "repo": repo,
                "paths_to_try": [
                    f"roles/{role}/defaults/main.yml",
                    f"roles/{role}/defaults/main.yaml",
                ],
                "purpose": "role_defaults",
                "fetch_method": "try_variations",
            }
        )

    # Task file (always include)
    task_entry = {
        "owner": owner,
        "repo": repo,
        "path": file_path,
        "purpose": "failed_task_code",
        "fetch_method": "direct",
        "line_context": {
            "target_line": line_number,
            "context_before": 10,
            "context_after": 10,
        },
    }

    if not role:
        task_entry["warning"] = "Could not extract role - defaults unavailable"

    paths.append(task_entry)
    return paths


def parse_github_paths(job_context: dict[str, Any]) -> dict[str, Any]:
    """Parse job context and build GitHub investigation paths."""
    job_id = job_context.get("job_id", "")
    job_name = job_context.get("job_name", "")
    guid = job_context.get("guid", "")
    failed_tasks = job_context.get("failed_tasks", [])

    metadata = parse_job_name(job_name, guid)
    warnings = metadata.get("warnings", [])
    enriched_tasks = []
    repos = set()

    for task in failed_tasks:
        task_path = task.get("task_path", "")
        location = parse_task_path(task_path)

        if location.get("owner") and location.get("repo"):
            repos.add(f"{location['owner']}/{location['repo']}")

        workload_paths = build_workload_paths(
            location.get("owner", ""),
            location.get("repo", ""),
            location.get("file_path", ""),
            location.get("line_number", 0),
        )

        config_hierarchy = build_agnosticv_hierarchy(
            metadata.get("platform", ""),
            metadata.get("catalog_item", ""),
            metadata.get("env", ""),
        )

        repos.add("rhpds/agnosticv")
        enriched_tasks.append(
            {
                "task_name": task.get("task", ""),
                "play": task.get("play", ""),
                "role": task.get("role", ""),
                "task_action": task.get("task_action", ""),
                "error_message": task.get("error_message", ""),
                "duration": task.get("duration", 0),
                "timestamp": task.get("timestamp", ""),
                "location": {"original_path": task_path, "parsed": location},
                "investigation_targets": {
                    "workload_code": workload_paths,
                    "configuration": {
                        "hierarchy": config_hierarchy,
                        "override_order": "Later files override earlier ones (1→2→3)",
                    },
                },
            }
        )

    total_files = sum(
        len(t["investigation_targets"]["configuration"]["hierarchy"])
        + len(t["investigation_targets"]["workload_code"])
        for t in enriched_tasks
    )

    discovery_hints = {
        "platform_dir": metadata.get("platform", "").replace("-", "_"),
        "catalog_guess": metadata.get("catalog_item", ""),
        "fallback_strategy": "If all paths fail: (1) Use mcp__github__get_file_contents to list parent directory, (2) Fuzzy match catalog name, (3) Try discovered path",
    }

    path_tracking = {
        "paths_attempted": [],  # Claude fills: [{purpose, path, result: "success|404"}]
        "paths_succeeded": {},  # Claude fills: {purpose: actual_path}
    }

    return {
        "job_id": job_id,
        "job_name": job_name,
        "parsing_status": "success" if not warnings else "success_with_warnings",
        "warnings": warnings,
        "parsed_metadata": metadata,
        "failed_tasks": enriched_tasks,
        "discovery_hints": discovery_hints,
        "path_tracking": path_tracking,
        "fetch_instructions": {
            "total_files": total_files,
            "repositories": sorted(list(repos)),
            "note": "Use paths_to_try when present, otherwise use path directly",
        },
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python parse_github_paths.py <step1_job_context.json>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    with open(input_file) as f:
        job_context = json.load(f)

    result = parse_github_paths(job_context)
    output_file = input_file.parent / "step4a_github_paths.json"

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Parsed GitHub paths for job {result.get('job_id', 'unknown')}")
    print(f"Output: {output_file}")
    print(f"\nFound {len(result.get('failed_tasks', []))} failed task(s)")

    for task in result.get("failed_tasks", []):
        t = task.get("investigation_targets", {})
        print(f"\n  Task: {task.get('task_name', '')[:60]} | Role: {task.get('role', '')}")
        print(
            f"  Paths: {len(t.get('workload_code', []))} workload, {len(t.get('configuration', {}).get('hierarchy', []))} config"
        )


if __name__ == "__main__":
    main()

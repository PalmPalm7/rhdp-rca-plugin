#!/usr/bin/env python3
"""
Step 4: Fetch GitHub Data - Parse paths and fetch all relevant files

Fetches all relevant GitHub configuration and workload files.
Real analysis happens in Step 5 when Claude reads and interprets the files.

Usage:
    python -m scripts.step4_fetch_github --job-id <JOB_ID>
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests


class GitHubClient:
    """GitHub API client for fetching files"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_file_content(self, owner: str, repo: str, path: str) -> dict | None:
        """Fetch file content from GitHub API"""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # Decode base64 content
                content = base64.b64decode(data["content"]).decode("utf-8")
                return {"path": path, "content": content, "sha": data["sha"], "size": data["size"]}
            elif response.status_code == 404:
                return None
            else:
                print(f"[WARNING] GitHub API error for {path}: {response.status_code}")
                return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch {path}: {e}")
            return None

    def try_path_variations(self, owner: str, repo: str, paths: list[str]) -> dict:
        """Try multiple path variations until one succeeds"""
        paths_tried = []

        for path in paths:
            result = self.get_file_content(owner, repo, path)
            status = "success" if result else "404"
            paths_tried.append({"path": path, "status": status})

            if result:
                result["paths_tried"] = paths_tried
                return result

        # All paths failed
        return {"error": "all_paths_failed", "paths_tried": paths_tried}


# Step 4a: Parse GitHub Paths Functions
def parse_job_name(job_name: str, guid: str) -> dict[str, Any]:
    """Parse RHPDS job name using GUID as anchor."""
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


def build_agnosticv_hierarchy(platform: str, catalog: str, env: str) -> list[dict[str, Any]]:
    """Build AgnosticV configuration hierarchy with path variations."""
    hierarchy = [
        {
            "order": 1,
            "owner": "rhpds",
            "repo": "agnosticv",
            "purpose": "base_defaults",
            "path": "common.yaml",
            "fetch_method": "direct",
        }
    ]
    platform_norm = platform.replace("-", "_") if platform else ""

    if platform:
        hierarchy.append(
            {
                "order": 2,
                "owner": "rhpds",
                "repo": "agnosticv",
                "purpose": "platform_config",
                "paths_to_try": [f"{platform_norm}/account.yaml", f"{platform}/account.yaml"],
                "fetch_method": "try_variations",
                "check_for": ["includes/secrets", "!vault"],
                "note": "Try underscore variant first",
            }
        )

    if platform and catalog:
        # Catalog item common.yaml (main config for the catalog item)
        catalog_common_paths = [f"{platform_norm}/{catalog}/common.yaml"]
        if platform != platform_norm:
            catalog_common_paths.append(f"{platform}/{catalog}/common.yaml")

        hierarchy.append(
            {
                "order": 3,
                "owner": "rhpds",
                "repo": "agnosticv",
                "purpose": "catalog_common",
                "paths_to_try": catalog_common_paths,
                "fetch_method": "try_variations",
                "note": "Catalog item main configuration (workloads, variables)",
            }
        )

    if platform and catalog and env:
        # Environment-specific overrides
        env_paths = [f"{platform_norm}/{catalog}/{env}.yaml"]
        if platform != platform_norm:
            env_paths.append(f"{platform}/{catalog}/{env}.yaml")

        hierarchy.append(
            {
                "order": 4,
                "owner": "rhpds",
                "repo": "agnosticv",
                "purpose": "env_overrides",
                "paths_to_try": env_paths,
                "fetch_method": "try_variations",
                "note": "Environment-specific overrides (dev, prod, event)",
            }
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


class Step4Analyzer:
    """Step 4: Parse paths, fetch files, analyze, generate root cause"""

    def __init__(self, job_id: str, base_dir: Path, github_client: GitHubClient):
        self.job_id = job_id
        self.base_dir = base_dir
        self.analysis_dir = base_dir / ".analysis" / job_id
        self.github = github_client

    def load_step1(self) -> dict:
        """Load Step 1 job context"""
        step1_file = self.analysis_dir / "step1_job_context.json"
        if not step1_file.exists():
            raise FileNotFoundError(f"Step 1 output not found: {step1_file}")

        with open(step1_file) as f:
            return json.load(f)

    def parse_github_paths(self, job_context: dict) -> dict:
        """Step 4a: Parse GitHub paths from job metadata"""
        print("[INFO] Step 4a: Parsing GitHub paths...")

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
                            "override_order": "Later files override earlier ones (1→2→3→4)",
                        },
                    },
                }
            )

        return {
            "job_id": job_id,
            "job_name": job_name,
            "parsing_status": "success" if not warnings else "success_with_warnings",
            "warnings": warnings,
            "parsed_metadata": metadata,
            "failed_tasks": enriched_tasks,
        }

    def fetch_configs(self, investigation_targets: dict) -> dict:
        """Step 4b: Fetch all AgnosticV configuration files"""
        print("[INFO] Step 4b: Fetching AgnosticV configurations...")

        fetched_configs = {}
        hierarchy = investigation_targets.get("configuration", {}).get("hierarchy", [])

        for config in hierarchy:
            order = config.get("order")
            purpose = config.get("purpose")
            owner = config.get("owner")
            repo = config.get("repo")

            print(f"  [{order}] Fetching {purpose}...")

            if "path" in config:
                # Direct fetch
                result = self.github.get_file_content(owner, repo, config["path"])
                if result:
                    fetched_configs[purpose] = result
                else:
                    fetched_configs[purpose] = {"error": "not_found", "path": config["path"]}

            elif "paths_to_try" in config:
                # Try all variations
                result = self.github.try_path_variations(owner, repo, config["paths_to_try"])
                fetched_configs[purpose] = result

        return fetched_configs

    def fetch_workload_code(self, investigation_targets: dict) -> dict:
        """Step 4c: Fetch all AgnosticD workload code"""
        print("[INFO] Step 4c: Fetching AgnosticD workload code...")

        fetched_workload = {}
        workload_files = investigation_targets.get("workload_code", [])

        for workload in workload_files:
            purpose = workload.get("purpose")
            owner = workload.get("owner")
            repo = workload.get("repo")

            print(f"  Fetching {purpose}...")

            if "path" in workload:
                result = self.github.get_file_content(owner, repo, workload["path"])
                fetched_workload[purpose] = result

            elif "paths_to_try" in workload:
                result = self.github.try_path_variations(owner, repo, workload["paths_to_try"])
                fetched_workload[purpose] = result

        return fetched_workload

    def run(self) -> dict:
        """Execute full Step 4 - fetch all GitHub files"""
        print(f"[INFO] Starting Step 4 analysis for job {self.job_id}...")

        # Load Step 1 context
        job_context = self.load_step1()

        # Step 4a: Parse GitHub paths
        github_paths = self.parse_github_paths(job_context)

        # For each failed task, fetch files
        enriched_tasks = []

        for task in github_paths.get("failed_tasks", []):
            investigation_targets = task.get("investigation_targets", {})

            # Step 4b: Fetch configs
            fetched_configs = self.fetch_configs(investigation_targets)

            # Step 4c: Fetch workload code
            fetched_workload = self.fetch_workload_code(investigation_targets)

            # Add fetched files to task
            enriched_task = {
                "task_name": task.get("task_name"),
                "play": task.get("play"),
                "role": task.get("role"),
                "task_action": task.get("task_action"),
                "error_message": task.get("error_message"),
                "duration": task.get("duration"),
                "timestamp": task.get("timestamp"),
                "location": task.get("location"),
                "fetched_configs": fetched_configs,
                "fetched_workload": fetched_workload,
            }

            enriched_tasks.append(enriched_task)

        # Combine into final output
        result = {
            "job_id": self.job_id,
            "job_metadata": github_paths.get("parsed_metadata", {}),
            "failed_tasks": enriched_tasks,
        }

        # Save output
        output_file = self.analysis_dir / "step4_github_fetch_history.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"[SUCCESS] Analysis complete: {output_file}")

        return result


def main():
    parser = argparse.ArgumentParser(
        description="Step 4: Fetch all relevant GitHub configuration and workload files"
    )
    parser.add_argument("--job-id", required=True, help="Job ID to analyze")
    args = parser.parse_args()

    # Get skill directory
    skill_dir = Path(__file__).parent.parent

    # Analysis files are in this skill's .analysis directory
    analysis_dir = skill_dir / ".analysis" / args.job_id
    if not analysis_dir.parent.exists():
        analysis_dir.parent.mkdir(parents=True, exist_ok=True)

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token or github_token == "your-github-token":
        print("[ERROR] GITHUB_TOKEN not found in environment variables")
        print("Get token from: https://github.com/settings/tokens")
        sys.exit(1)

    # Initialize clients
    github_client = GitHubClient(github_token)

    # Run analysis (using this skill's .analysis directory)
    analyzer = Step4Analyzer(args.job_id, skill_dir, github_client)
    analyzer.run()


if __name__ == "__main__":
    main()

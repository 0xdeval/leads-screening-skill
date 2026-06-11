#!/usr/bin/env python3
"""Deterministic bookkeeping utilities for the candidate-screening skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_RELATIVE_PATH = Path(".candidate-screening") / "manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify_name(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unknown-candidate"


def read_manifest(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / MANIFEST_RELATIVE_PATH
    if not manifest_path.exists():
        return {}
    with manifest_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def write_manifest(project_root: Path, manifest: dict[str, Any]) -> None:
    manifest_path = project_root / MANIFEST_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as file_handle:
        json.dump(manifest, file_handle, indent=2, sort_keys=True)
        file_handle.write("\n")


def status(project_root: Path) -> dict[str, Any]:
    manifest = read_manifest(project_root)
    job_path = project_root / "job-description.md"
    portrait_path = project_root / "candidate-portrait.md"
    leads_dir = project_root / "potential-leads"

    current_job_hash = sha256_file(job_path) if job_path.exists() else None
    current_portrait_hash = sha256_file(portrait_path) if portrait_path.exists() else None

    lead_statuses = []
    if leads_dir.exists():
        for lead_path in sorted(path for path in leads_dir.iterdir() if path.is_file()):
            relative = lead_path.relative_to(project_root).as_posix()
            current_lead_hash = sha256_file(lead_path)
            manifest_lead = manifest.get("leads", {}).get(relative, {})
            report_path_value = manifest_lead.get("report_path")
            report_exists = bool(report_path_value and (project_root / report_path_value).exists())
            lead_changed = manifest_lead.get("lead_hash") != current_lead_hash
            screening_status = manifest_lead.get("screening_status", "not_checked")
            lead_statuses.append(
                {
                    "source_file": relative,
                    "lead_hash": current_lead_hash,
                    "report_path": report_path_value,
                    "report_exists": report_exists,
                    "screening_status": screening_status,
                    "checked_at": manifest_lead.get("checked_at"),
                    "eligible_for_screening": (
                        screening_status != "checked_not_proceeded" or lead_changed
                    ),
                    "stale": (
                        not report_exists
                        or lead_changed
                        or manifest_lead.get("job_description_hash") != current_job_hash
                        or manifest_lead.get("candidate_portrait_hash") != current_portrait_hash
                    ),
                }
            )

    return {
        "job_description_exists": job_path.exists(),
        "job_description_hash": current_job_hash,
        "candidate_portrait_exists": portrait_path.exists(),
        "candidate_portrait_hash": current_portrait_hash,
        "candidate_portrait_stale": (
            not portrait_path.exists()
            or manifest.get("job_description_hash") != current_job_hash
            or manifest.get("candidate_portrait_hash") != current_portrait_hash
        ),
        "lead_count": len(lead_statuses),
        "leads": lead_statuses,
        "manifest_exists": bool(manifest),
        "checked_at": utc_now(),
    }


def update_manifest_hashes(project_root: Path) -> dict[str, Any]:
    manifest = read_manifest(project_root)
    job_path = project_root / "job-description.md"
    portrait_path = project_root / "candidate-portrait.md"

    if job_path.exists():
        manifest["job_description_hash"] = sha256_file(job_path)
    if portrait_path.exists():
        manifest["candidate_portrait_hash"] = sha256_file(portrait_path)
        manifest["candidate_portrait_updated_at"] = utc_now()

    manifest.setdefault("leads", {})
    write_manifest(project_root, manifest)
    return manifest


def mark_checked(
    project_root: Path,
    source_file: str,
    report_path: str,
    score: int,
) -> dict[str, Any]:
    lead_path = project_root / source_file
    candidate_report_path = project_root / report_path
    if not lead_path.is_file():
        raise FileNotFoundError(f"Lead file not found: {source_file}")
    if not candidate_report_path.is_file():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    manifest = read_manifest(project_root)
    manifest.setdefault("leads", {})
    timestamp = utc_now()
    manifest["leads"][source_file] = {
        "candidate_portrait_hash": (
            sha256_file(project_root / "candidate-portrait.md")
            if (project_root / "candidate-portrait.md").exists()
            else None
        ),
        "checked_at": timestamp,
        "job_description_hash": (
            sha256_file(project_root / "job-description.md")
            if (project_root / "job-description.md").exists()
            else None
        ),
        "lead_hash": sha256_file(lead_path),
        "report_hash": sha256_file(candidate_report_path),
        "report_path": report_path,
        "score": score,
        "screening_status": "checked_not_proceeded",
        "updated_at": timestamp,
    }
    write_manifest(project_root, manifest)
    return manifest["leads"][source_file]


def main() -> None:
    parser = argparse.ArgumentParser(description="Candidate screening bookkeeping utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show freshness status")
    status_parser.add_argument("project_root", type=Path)

    hash_parser = subparsers.add_parser("hash", help="Hash a file")
    hash_parser.add_argument("file", type=Path)

    slug_parser = subparsers.add_parser("slug", help="Slugify a candidate name")
    slug_parser.add_argument("name")

    update_parser = subparsers.add_parser("update-manifest", help="Update job and portrait hashes")
    update_parser.add_argument("project_root", type=Path)

    checked_parser = subparsers.add_parser(
        "mark-checked",
        help="Mark a processed lead as checked and not proceeded",
    )
    checked_parser.add_argument("project_root", type=Path)
    checked_parser.add_argument("source_file")
    checked_parser.add_argument("report_path")
    checked_parser.add_argument("score", type=int)

    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps(status(args.project_root.resolve()), indent=2, sort_keys=True))
    elif args.command == "hash":
        print(sha256_file(args.file.resolve()))
    elif args.command == "slug":
        print(slugify_name(args.name))
    elif args.command == "update-manifest":
        print(json.dumps(update_manifest_hashes(args.project_root.resolve()), indent=2, sort_keys=True))
    elif args.command == "mark-checked":
        print(
            json.dumps(
                mark_checked(
                    args.project_root.resolve(),
                    args.source_file,
                    args.report_path,
                    args.score,
                ),
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()

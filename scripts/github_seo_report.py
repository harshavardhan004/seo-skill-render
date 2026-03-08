#!/usr/bin/env python3
"""
GitHub SEO Report Generator

Runs GitHub SEO scripts and combines their outputs into a single markdown report.

Usage:
  python github_seo_report.py --repo owner/repo --markdown GITHUB-SEO-REPORT.md
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from github_api import get_token, resolve_repo


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_json_script(script_name: str, extra_args: list) -> dict:
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path] + extra_args + ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {
            "ok": False,
            "error": (result.stderr or result.stdout or f"Exit {result.returncode}").strip(),
            "returncode": result.returncode,
        }
    try:
        payload = json.loads((result.stdout or "").strip() or "{}")
        return {"ok": True, "data": payload}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"Invalid JSON from {script_name}: {exc}", "returncode": 1}


def collect_inputs(args, repo: str, token: str) -> dict:
    common = ["--repo", repo, "--provider", args.provider]
    if token:
        common += ["--token", token]

    benchmark_args = common[:]
    if args.query:
        for query in args.query:
            benchmark_args += ["--query", query]
    if args.query_file:
        benchmark_args += ["--query-file", args.query_file]
    benchmark_args += ["--max-pages", str(args.max_pages), "--per-page", str(args.per_page)]
    competitor_args = benchmark_args[:] + ["--top-n", str(args.competitor_top_n)]

    traffic_args = common + ["--archive-dir", args.archive_dir]
    if args.no_archive_write:
        traffic_args += ["--no-write"]

    return {
        "repo_audit": ["github_repo_audit.py", common],
        "readme_lint": ["github_readme_lint.py", [args.readme_path]],
        "community_health": ["github_community_health.py", common],
        "search_benchmark": ["github_search_benchmark.py", benchmark_args],
        "competitor_research": ["github_competitor_research.py", competitor_args],
        "traffic_archiver": ["github_traffic_archiver.py", traffic_args],
    }


def extract_score(outputs: dict) -> dict:
    score_map = {}
    if outputs.get("repo_audit", {}).get("ok"):
        score_map["repo_audit"] = outputs["repo_audit"]["data"].get("summary", {}).get("score")
    if outputs.get("readme_lint", {}).get("ok"):
        score_map["readme_lint"] = outputs["readme_lint"]["data"].get("summary", {}).get("score")
    if outputs.get("community_health", {}).get("ok"):
        score_map["community_health"] = outputs["community_health"]["data"].get("score")
    valid = [v for v in score_map.values() if isinstance(v, (int, float))]
    overall = round(sum(valid) / len(valid), 2) if valid else None
    return {"components": score_map, "overall": overall}


def collect_findings(outputs: dict) -> list:
    findings = []
    for key in ("repo_audit", "readme_lint", "community_health"):
        item = outputs.get(key, {})
        if not item.get("ok"):
            continue
        for finding in item["data"].get("findings", []):
            findings.append(
                {
                    "source": key,
                    "severity": finding.get("severity", "Info"),
                    "finding": finding.get("finding", ""),
                    "evidence": finding.get("evidence", ""),
                    "fix": finding.get("fix", ""),
                    "confidence": finding.get("confidence", "Likely"),
                }
            )
    competitor = outputs.get("competitor_research", {})
    if competitor.get("ok"):
        for opp in competitor.get("data", {}).get("gaps", {}).get("opportunities", []):
            findings.append(
                {
                    "source": "competitor_research",
                    "severity": opp.get("severity", "Info"),
                    "finding": opp.get("finding", ""),
                    "evidence": opp.get("evidence", ""),
                    "fix": opp.get("fix", ""),
                    "confidence": "Likely",
                }
            )
    severity_order = {"Critical": 0, "Warning": 1, "Pass": 2, "Info": 3}
    findings.sort(key=lambda x: severity_order.get(x["severity"], 9))
    return findings


def build_backlink_plan(outputs: dict) -> dict:
    """Create a practical backlink and promotion plan for the repository."""
    repo_audit = outputs.get("repo_audit", {})
    metadata = {}
    title_analysis = {}
    if repo_audit.get("ok"):
        metadata = repo_audit.get("data", {}).get("metadata", {}) or {}
        title_analysis = repo_audit.get("data", {}).get("title_analysis", {}) or {}

    keywords = title_analysis.get("search_intent_keywords", [])[:6]
    base_title = title_analysis.get("recommended_display_title") or metadata.get("name") or "Repository"
    repo_url = metadata.get("html_url")
    if not repo_url:
        repo_slug = metadata.get("full_name")
        if repo_slug:
            repo_url = f"https://github.com/{repo_slug}"

    title_ideas = [
        f"How I Built {base_title} for SEO Automation",
        f"GitHub SEO Playbook: Improving Discoverability for {base_title}",
        f"{base_title}: From Idea to Open-Source SEO Workflow",
    ]
    if keywords:
        kw_phrase = ", ".join(keywords[:3])
        title_ideas.append(f"Open-Source Guide: {kw_phrase} with {base_title}")

    channels = [
        {
            "channel": "Medium",
            "type": "Technical case study",
            "cadence": "1 post per major release",
            "cta": "Link to repo + install quickstart + release notes",
        },
        {
            "channel": "Dev.to",
            "type": "Tutorial / launch post",
            "cadence": "1 launch post + update posts quarterly",
            "cta": "Link to GitHub repo and usage examples",
        },
        {
            "channel": "Hashnode",
            "type": "Deep-dive engineering write-up",
            "cadence": "Bi-monthly",
            "cta": "Link to architecture docs and scripts",
        },
        {
            "channel": "Personal/Company Blog",
            "type": "Canonical long-form article",
            "cadence": "Monthly",
            "cta": "Link to repo, docs, and comparison pages",
        },
        {
            "channel": "LinkedIn Article",
            "type": "Problem/solution summary for practitioners",
            "cadence": "Per release",
            "cta": "Link to repo and demo outputs",
        },
        {
            "channel": "Reddit (relevant subreddits)",
            "type": "Show-and-tell with value-first context",
            "cadence": "Selective (major feature drops)",
            "cta": "Share repo only after explaining workflow and results",
        },
    ]

    anchor_guidance = {
        "exact_match_max_percent": 10,
        "recommended_mix": [
            "Brand anchors (repo/owner name)",
            "Partial-match anchors (e.g., 'agentic SEO skill')",
            "Generic anchors ('GitHub repo', 'source code')",
            "Naked URL anchors",
        ],
    }

    return {
        "repo_url": repo_url,
        "title_ideas": title_ideas[:4],
        "channels": channels,
        "anchor_text_guidance": anchor_guidance,
    }


def build_markdown(report: dict) -> str:
    lines = []
    lines.append("# GitHub SEO Report")
    lines.append("")
    lines.append(f"- Repository: `{report['repo']}`")
    lines.append(f"- Generated (UTC): `{report['timestamp_utc']}`")
    lines.append(f"- Provider mode: `{report['provider']}`")
    lines.append(f"- Overall score: `{report['scores']['overall']}`")
    lines.append("")

    lines.append("## Score Components")
    lines.append("")
    lines.append("| Component | Score |")
    lines.append("|-----------|-------|")
    for key, value in report["scores"]["components"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")

    lines.append("## Script Status")
    lines.append("")
    lines.append("| Script | Status |")
    lines.append("|--------|--------|")
    for key, payload in report["outputs"].items():
        status = "ok" if payload.get("ok") else f"failed: {payload.get('error', 'unknown')}"
        lines.append(f"| {key} | {status} |")
    lines.append("")

    if report["limitations"]:
        lines.append("## Limitations")
        lines.append("")
        for item in report["limitations"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Prioritized Findings")
    lines.append("")
    lines.append("| Severity | Source | Finding | Evidence | Fix |")
    lines.append("|----------|--------|---------|----------|-----|")
    for finding in report["findings"][:40]:
        lines.append(
            "| {severity} | {source} | {finding} | {evidence} | {fix} |".format(
                severity=finding["severity"],
                source=finding["source"],
                finding=finding["finding"].replace("|", "/"),
                evidence=finding["evidence"].replace("|", "/"),
                fix=finding["fix"].replace("|", "/"),
            )
        )
    if not report["findings"]:
        lines.append("| Pass | system | No major findings captured. | n/a | Continue monitoring. |")
    lines.append("")

    benchmark = report["outputs"].get("search_benchmark", {})
    if benchmark.get("ok"):
        data = benchmark["data"]
        lines.append("## Query Benchmark")
        lines.append("")
        lines.append("| Query | Rank | Sampled | Total Results |")
        lines.append("|-------|------|---------|---------------|")
        for item in data.get("results", []):
            rank = item["target_rank"] if item["target_rank"] is not None else "Not found"
            lines.append(
                f"| {item['query']} | {rank} | {item.get('sampled_results')} | {item.get('total_count')} |"
            )
        lines.append("")

    competitor = report["outputs"].get("competitor_research", {})
    if competitor.get("ok"):
        comp_data = competitor["data"]
        lines.append("## Competitor Research")
        lines.append("")
        summary = comp_data.get("summary", {})
        lines.append(
            f"- Competitors analyzed: `{summary.get('competitors_analyzed', 0)}` "
            f"across `{summary.get('queries_used', 0)}` queries"
        )
        lines.append("")
        lines.append("| Competitor | Seen Queries | Best Rank | Stars | Topics |")
        lines.append("|------------|--------------|-----------|-------|--------|")
        for item in comp_data.get("competitors", [])[:10]:
            md = item.get("metadata", {})
            lines.append(
                f"| {item.get('full_name')} | {item.get('seen_in_queries')} | {item.get('best_rank')} | "
                f"{md.get('stargazers_count')} | {len(md.get('topics') or [])} |"
            )
        if not comp_data.get("competitors"):
            lines.append("| n/a | 0 | n/a | n/a | n/a |")
        lines.append("")
        gap_data = comp_data.get("gaps", {})
        lines.append("### Topic Gaps")
        lines.append("")
        topic_gaps = gap_data.get("topic_gaps", [])[:10]
        if topic_gaps:
            for gap in topic_gaps:
                lines.append(
                    f"- `{gap.get('topic')}` (covered by {gap.get('covered_by_competitors')} competitors)"
                )
        else:
            lines.append("- No high-confidence topic gaps detected from current sample.")
        lines.append("")
        lines.append("### Competitor Opportunities")
        lines.append("")
        opportunities = gap_data.get("opportunities", [])
        if opportunities:
            for opp in opportunities:
                lines.append(f"- [{opp.get('severity', 'Info')}] {opp.get('finding')}")
                lines.append(f"  Evidence: {opp.get('evidence')}")
                lines.append(f"  Fix: {opp.get('fix')}")
        else:
            lines.append("- No additional competitor-derived opportunities captured.")
        lines.append("")

    traffic = report["outputs"].get("traffic_archiver", {})
    if traffic.get("ok"):
        snap = traffic["data"].get("snapshot", {})
        totals = snap.get("totals", {})
        lines.append("## Traffic Snapshot")
        lines.append("")
        lines.append(
            f"- Views: `{totals.get('views_count')}` (unique: `{totals.get('views_uniques')}`)"
        )
        lines.append(
            f"- Clones: `{totals.get('clones_count')}` (unique: `{totals.get('clones_uniques')}`)"
        )
        archive_paths = traffic["data"].get("archive_paths", {})
        if archive_paths:
            lines.append(f"- Archive history: `{archive_paths.get('traffic_history')}`")
            lines.append(f"- Latest snapshot: `{archive_paths.get('latest_snapshot')}`")
        lines.append("")

    title_analysis = report.get("title_analysis", {})
    if title_analysis:
        lines.append("## Title Optimization")
        lines.append("")
        lines.append(f"- Current name: `{title_analysis.get('current_name')}`")
        lines.append(f"- Recommended slug: `{title_analysis.get('recommended_repo_slug')}`")
        lines.append(f"- Recommended title: `{title_analysis.get('recommended_display_title')}`")
        keywords = title_analysis.get("search_intent_keywords", [])
        if keywords:
            lines.append(f"- Intent keywords: `{', '.join(keywords)}`")
        lines.append("")

    backlink_plan = report.get("backlink_plan", {})
    if backlink_plan:
        lines.append("## Backlink Distribution Plan")
        lines.append("")
        if backlink_plan.get("repo_url"):
            lines.append(f"- Target repo URL: `{backlink_plan.get('repo_url')}`")
        lines.append("")
        lines.append("### Suggested Post Titles")
        lines.append("")
        for title in backlink_plan.get("title_ideas", []):
            lines.append(f"- {title}")
        lines.append("")
        lines.append("### Channels")
        lines.append("")
        lines.append("| Channel | Content Type | Cadence | CTA |")
        lines.append("|---------|--------------|---------|-----|")
        for item in backlink_plan.get("channels", []):
            lines.append(
                f"| {item['channel']} | {item['type']} | {item['cadence']} | {item['cta']} |"
            )
        lines.append("")
        anchor = backlink_plan.get("anchor_text_guidance", {})
        lines.append("### Anchor Guidance")
        lines.append("")
        lines.append(
            f"- Exact-match anchor cap: `{anchor.get('exact_match_max_percent', 10)}%`"
        )
        for mix in anchor.get("recommended_mix", []):
            lines.append(f"- {mix}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate consolidated GitHub SEO report from local script outputs.")
    parser.add_argument("--repo", help="Repository slug or URL (owner/repo). If omitted, infer from git origin.")
    parser.add_argument("--token", help="GitHub token override. Prefer env vars GITHUB_TOKEN or GH_TOKEN.")
    parser.add_argument(
        "--provider",
        choices=["auto", "api", "gh"],
        default="auto",
        help="GitHub data provider mode (default: auto).",
    )
    parser.add_argument("--readme-path", default="README.md", help="README path for linting (default: README.md)")
    parser.add_argument("--query", action="append", help="Search query for benchmark (repeatable).")
    parser.add_argument("--query-file", help="Path to query list file.")
    parser.add_argument("--max-pages", type=int, default=2, help="Search pages per query (default: 2).")
    parser.add_argument("--per-page", type=int, default=50, help="Search results per page (default: 50).")
    parser.add_argument("--competitor-top-n", type=int, default=6, help="Competitors to analyze in depth (default: 6).")
    parser.add_argument("--archive-dir", default=".github-seo-data", help="Traffic archive directory.")
    parser.add_argument("--no-archive-write", action="store_true", help="Do not write traffic archive files.")
    parser.add_argument("--markdown", default="GITHUB-SEO-REPORT.md", help="Output markdown path.")
    parser.add_argument("--json", action="store_true", help="Output merged JSON.")
    parser.add_argument("--output", help="Write merged JSON to file path.")
    args = parser.parse_args()

    try:
        repo = resolve_repo(args.repo)
        token = get_token(args.token)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    plan = collect_inputs(args=args, repo=repo, token=token)
    outputs = {}
    limitations = []

    for key, (script_name, extra_args) in plan.items():
        result = run_json_script(script_name, extra_args)
        outputs[key] = result
        if not result.get("ok"):
            limitations.append(f"{key} failed: {result.get('error', 'unknown')}")
        else:
            for item in result["data"].get("limitations", []):
                limitations.append(f"{key}: {item}")
            if key == "traffic_archiver":
                snapshot = result["data"].get("snapshot", {})
                for item in snapshot.get("limitations", []):
                    limitations.append(f"{key}: {item}")

    report = {
        "timestamp_utc": utc_now_iso(),
        "repo": repo,
        "provider": args.provider,
        "outputs": outputs,
        "limitations": limitations,
    }
    report["scores"] = extract_score(outputs)
    report["findings"] = collect_findings(outputs)
    report["title_analysis"] = outputs.get("repo_audit", {}).get("data", {}).get("title_analysis", {})
    report["backlink_plan"] = build_backlink_plan(outputs)
    report["markdown_path"] = args.markdown

    markdown = build_markdown(report)
    with open(args.markdown, "w", encoding="utf-8") as f:
        f.write(markdown)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Generated markdown report: {args.markdown}")
        if limitations:
            print("Limitations:")
            for item in limitations[:10]:
                print(f"- {item}")


if __name__ == "__main__":
    main()

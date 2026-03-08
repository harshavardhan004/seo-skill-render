---
name: seo-github
description: >
  GitHub repository SEO and discoverability analysis. Use for repository search
  visibility, README conversion optimization, community health checks, topic
  strategy, and traffic archival planning.
---

# GitHub Repository SEO

Apply `resources/references/llm-audit-rubric.md` for evidence format and
confidence labels, and apply `resources/references/readme-audit-rubric.md`
for README scoring.

## Trigger Mapping

Use this workflow when the user asks:

- "GitHub SEO"
- "optimize this repo for GitHub search"
- "improve repository discoverability"
- "README SEO audit"
- "topics and metadata optimization"
- "community profile audit"

## Inputs

- Repository URL or slug (`owner/repo`).
- Optional target query set for GitHub search benchmarking.
- Optional GitHub token (`GITHUB_TOKEN` or `GH_TOKEN`) for API checks.

### Auth Setup

Use either environment token or `gh` auth:

```bash
# Option A: token env vars (recommended for automation)
export GITHUB_TOKEN="ghp_xxx"
# or
export GH_TOKEN="ghp_xxx"

# Option B: GitHub CLI login fallback
gh auth login -h github.com
gh auth status -h github.com
```

## Workflow

### 1. Resolve Scope and Access

- Resolve target repo from input or local `origin` remote.
- Check whether token-based API access is available.
- If token is missing/invalid, continue with partial checks and mark API-based
  findings as `Unknown` or `Likely`.

### 2. Run Evidence Scripts

Run scripts from `<SKILL_DIR>/scripts/`:

```bash
python3 github_repo_audit.py --repo <owner/repo> --provider auto --json
python3 github_readme_lint.py README.md --json
python3 github_community_health.py --repo <owner/repo> --provider auto --json
python3 github_search_benchmark.py --repo <owner/repo> --query "<query>" --provider auto --json
python3 github_competitor_research.py --repo <owner/repo> --query "<query>" --provider auto --top-n 6 --json
python3 github_traffic_archiver.py --repo <owner/repo> --provider auto --json
python3 github_seo_report.py --repo <owner/repo> --provider auto --markdown GITHUB-SEO-REPORT.md
```

### 3. Analyze by Area

- Metadata discoverability: repo name, description, topics, homepage, social preview.
- Title strategy: underscore vs hyphen checks, intent-keyword extraction, suggested slug/title.
- README SEO and conversion: heading structure, intent alignment, CTAs, proof sections.
- Community trust: governance files and contribution readiness.
- Search benchmarking: target query positions and sampled competitors.
- Competitor research: topic overlaps, README pattern gaps, and strategy opportunities.
- Traffic trend readiness: archival freshness and retention compliance.
- Backlink distribution: channel suggestions (Medium/blog/dev communities), post title ideas, and anchor-mix guidance.

### 4. Prioritize

Classify recommendations:

- `Critical`: blocks discovery, trust, or measurement continuity.
- `Warning`: important optimization opportunity.
- `Pass`: meets baseline.
- `Info`: contextual or optional enhancement.

### 5. Output Artifacts

Required for `seo github` runs:

- `GITHUB-SEO-REPORT.md` — findings and evidence.
- `GITHUB-ACTION-PLAN.md` — prioritized fixes.

Optional:

- `GITHUB-WEEKLY-SCORECARD.md` — recurring measurement snapshot.

## Delegation Guidance

- Strategy synthesis: `resources/agents/seo-github-analyst.md`
- Competitor/query benchmark: `resources/agents/seo-github-benchmark.md`
- API collection/archival: `resources/agents/seo-github-data.md`

## Critical Rules

1. Never claim a definitive GitHub ranking formula.
2. Treat token/API failures as environment limitations, not repo defects.
3. Keep topics relevant and capped at 20.
4. Preserve existing project voice/branding in README recommendations.
5. Archive traffic snapshots regularly due 14-day retention windows.

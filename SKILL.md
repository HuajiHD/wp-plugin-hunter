---
name: wp-plugin-audit-hunter
description: |
  Search WordPress.org plugins, download and extract selected plugin packages,
  then output a php-audit-pipeline handoff. This skill performs no vulnerability
  scanning, triage, confirmation, severity assignment, or reporting.
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Task
model: sonnet
priority: high
file_patterns:
  - "**/*.php"
  - "**/*.js"
  - "**/*.ts"
  - "**/*.json"
  - "**/*.txt"
  - "**/readme.txt"
exclude_patterns:
  - "**/vendor/**"
  - "**/node_modules/**"
  - "**/.git/**"
  - "**/tests/**"
  - "**/test/**"
---

# WordPress Plugin Audit Hunter

> Defensive WordPress plugin security audit skill.
> Goal: discover WordPress.org plugins, download/extract source archives, and hand off to PHP-Code-Audit-Skill's `php-audit-pipeline`.

## When to Use This Skill

Use this skill when the user asks to:

- Search WordPress plugins and audit them.
- Automatically download WordPress.org plugins for code review.
- Produce extracted plugin paths and fetch reports for `php-audit-pipeline`.

Trigger phrases:

- "自动搜索 wp 插件"
- "拉 wp 插件下来审计"
- "WordPress 插件漏洞挖掘"
- "找插件然后交给 php-audit-pipeline"
- "只负责拉取插件"

## Safety Boundary

This skill is for defensive local source-code audit only.

Allowed:

- Query WordPress.org plugin metadata APIs.
- Download public plugin ZIP packages from WordPress.org.
- Extract packages into a local workspace.
- Produce fetch reports and handoff JSON.
- Hand off extracted plugin paths to `php-audit-pipeline`.

Not allowed:

- Scanning or attacking live third-party WordPress sites.
- Brute force, credential attacks, spam, persistence, or destructive testing.
- Confirming vulnerabilities in this skill.
- Scanning or ranking vulnerabilities in this skill.
- Producing exploit details or PoC content in this skill.

## Required Companion Script

The automation entrypoint is:

```bash
python3 scripts/wp_plugin_hunter.py --help
```

The script performs:

1. WordPress.org plugin search.
2. ZIP download and extraction.
3. Safe ZIP extraction.
4. Fetch report generation.
5. Output extracted plugin paths and handoff data for `php-audit-pipeline`.

## Execution Controller

### Step 1: Authorization and Scope

Confirm that the target source is public WordPress.org plugins unless the user explicitly provides local plugin ZIPs or directories.

Required output:

```text
[SCOPE]
source: wordpress.org | local
search_terms: {terms or slugs}
max_plugins: {N}
network: metadata/download only
```

### Step 2: Workspace Setup

Create a disposable workspace outside any production project, for example:

```bash
mkdir -p ./wp-audit-runs
```

Required output:

```text
[WORKSPACE] {absolute path}
```

### Step 3: Automated Discovery and Fetch

Run the companion script. Examples:

```bash
python3 scripts/wp_plugin_hunter.py search \
  --query "booking" \
  --max-plugins 25 \
  --workspace ./wp-audit-runs
```

```bash
python3 scripts/wp_plugin_hunter.py slugs \
  --slug contact-form-7 \
  --slug woocommerce \
  --workspace ./wp-audit-runs
```

Required output:

```text
[FETCH]
downloaded: {count}
fetched: {plugin slug list}
report: {fetch report path}
```

### Step 4: Output Results and Hand Off

This skill stops after fetch output. Do not scan or confirm vulnerabilities here.

Required output:

```text
[FETCH_RESULT]
workspace: {absolute path}
downloaded: {count}
fetched: {count}
extracted_path: {path or none}
fetch_report: {json path or none}
summary: {summary json path}
```

### Step 5: Delegate Audit

After fetching, invoke `php-audit-pipeline` against the extracted plugin directory. The pipeline owns all audit, triage, confirmation, severity, and reporting. When the target is a WordPress plugin, the pipeline should use `php-wordpress-audit` for the framework-specific phase.

Required handoff wording:

```text
[HANDOFF_TO_PHP_AUDIT_PIPELINE]
source_path: {extracted plugin path}
output_path: {workspace}/audit/{plugin slug}
fetch_report: {json report path}
requested_skill: php-audit-pipeline
framework_skill: php-wordpress-audit
note: wp-plugin-audit-hunter only performed discovery/download/extraction.
```

## Scope Rules

Every fetch result should include:

- Plugin slug and version.
- Extracted plugin path.
- Fetch report path.
- PHP audit pipeline handoff.

Never do in this skill:

- Confirm a vulnerability.
- Claim exploitability.
- Assign final severity.
- Rank candidates.
- Scan plugin source for vulnerability patterns.
- Generate PoC payloads.
- Produce final vulnerability reports.

## Output Format

After fetching, report:

```markdown
## WordPress Plugin Fetch Result

- Workspace: `{path}`
- Downloaded: `{count}`
- Extracted path: `{path|none}`
- Fetch report: `{json path|none}`
- Summary: `{summary json path}`

## Next Step

Use `php-audit-pipeline` on `{extracted path}` with `php-wordpress-audit` for the WordPress framework phase. `wp-plugin-audit-hunter` does not provide vulnerability evidence.
```

## Version

- Current: 0.5.0
- Updated: 2026-05-20

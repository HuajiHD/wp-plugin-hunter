# wp-plugin-audit-hunter

Local defensive fetch-and-handoff skill for WordPress.org plugin packages.

It searches plugin metadata, downloads public plugin ZIP files, extracts them into
a disposable workspace, and outputs JSON handoff data. Vulnerability audit,
triage, confirmation, severity, and final reporting are delegated to
PHP-Code-Audit-Skill's `php-audit-pipeline`; WordPress-specific checks are
handled by `php-wordpress-audit`.

## Run

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

Reports are written under:

```text
./wp-audit-runs/reports/
```

## Install As A Skill

After review, copy or symlink this directory into your Codex skills directory:

```bash
cp -r wp-plugin-audit-hunter ~/.codex/skills/
```

Restart the agent session so the skill list refreshes.

## Notes

- The script only talks to WordPress.org metadata/download endpoints.
- It does not scan live WordPress sites.
- This skill does not scan plugin source for vulnerabilities.
- Use `php-audit-pipeline` for all audit, triage, confirmation, exploitability analysis, and final reporting.

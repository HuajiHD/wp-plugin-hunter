# WordPress Plugin Fetch Handoff

This reference belongs to `wp-plugin-audit-hunter`. It is not a vulnerability
confirmation guide. Use it to structure the context handed to `php-audit-pipeline`.

## Handoff Fields

Provide these fields when invoking `php-audit-pipeline`:

- Extracted plugin directory.
- Plugin slug and version.
- Fetch JSON report path.
- Output directory for the audit report.
- Framework skill hint: `php-wordpress-audit`.

## Suggested PHP Audit Pipeline Target

Point `php-audit-pipeline` at the extracted plugin directory, not the ZIP file:

```text
source_path: ./wp-audit-runs/plugins/{slug}/{plugin-root}
output_path: ./wp-audit-runs/audit/{slug}
fetch_report: ./wp-audit-runs/reports/{slug}.fetch.json
requested_skill: php-audit-pipeline
framework_skill: php-wordpress-audit
```

## Boundary

`wp-plugin-audit-hunter` only performs:

- WordPress.org metadata search.
- Public ZIP download.
- Safe local extraction.
- Fetch JSON output.

`php-audit-pipeline` performs:

- Full code audit.
- Source-to-sink confirmation.
- False-positive filtering.
- Exploitability analysis.
- Final vulnerability report.

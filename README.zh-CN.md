# wp-plugin-audit-hunter 中文说明

`wp-plugin-audit-hunter` 是一个 Codex skill，用于自动搜索、下载并解压 WordPress.org 插件，然后把源码路径交给 PHP 审计流水线处理。

它不做漏洞扫描、不做误报确认、不评严重等级，也不生成最终漏洞报告。所有审计工作都交给 PHP-Code-Audit-Skill 的 `php-audit-pipeline`，WordPress 专项检查由 `php-wordpress-audit` 负责。

## 适用场景

- 想按关键词批量搜索 WordPress.org 插件并拉取源码。
- 想指定插件 slug 下载官方 ZIP 包。
- 想把下载好的插件目录交给深度 PHP 白盒审计流程。
- 想避免插件抓取阶段提前产生误报或伪 Critical 结论。

## 工作边界

本 skill 只负责：

- 查询 WordPress.org 插件元数据接口。
- 下载 WordPress.org 官方插件 ZIP。
- 安全解压 ZIP，阻止路径穿越。
- 生成 fetch report 和 handoff JSON。
- 输出 `php-audit-pipeline` 所需的 `source_path`、`output_path`、`fetch_report`。

本 skill 不负责：

- 扫描 live WordPress 站点。
- 攻击第三方目标。
- 扫描源码中的漏洞模式。
- 判断漏洞是否成立。
- 输出 PoC、利用链或最终漏洞报告。
- 给漏洞分级或筛选 Critical。

## 安装

把目录复制到 Codex skills 目录：

```bash
cp -r wp-plugin-audit-hunter ~/.codex/skills/
```

然后重启 Codex 会话，让 skill 列表刷新。

如果要使用完整审计交接，建议同时安装 PHP-Code-Audit-Skill：

```bash
git clone https://github.com/0xShe/PHP-Code-Audit-Skill /tmp/PHP-Code-Audit-Skill
cp -r /tmp/PHP-Code-Audit-Skill/php-* ~/.codex/skills/
cp -r /tmp/PHP-Code-Audit-Skill/shared ~/.codex/skills/
```

关键审计入口：

- `php-audit-pipeline`：PHP 全链路白盒审计编排。
- `php-wordpress-audit`：WordPress 插件/主题专项审计。

## 使用方式

按关键词搜索并下载插件：

```bash
python3 scripts/wp_plugin_hunter.py search \
  --query "booking" \
  --max-plugins 10 \
  --workspace ./wp-audit-runs
```

按 slug 精确下载插件：

```bash
python3 scripts/wp_plugin_hunter.py slugs \
  --slug contact-form-7 \
  --slug woocommerce \
  --workspace ./wp-audit-runs
```

只下载第一个成功结果：

```bash
python3 scripts/wp_plugin_hunter.py search \
  --query "membership" \
  --max-plugins 20 \
  --first \
  --workspace ./wp-audit-runs
```

强制重新下载和解压：

```bash
python3 scripts/wp_plugin_hunter.py slugs \
  --slug hello-dolly \
  --force \
  --workspace ./wp-audit-runs
```

## 输出目录

默认输出到：

```text
./wp-audit-runs/
├── downloads/
├── plugins/
└── reports/
```

常见文件：

- `downloads/{slug}.{version}.zip`：下载的插件 ZIP。
- `plugins/{slug}/...`：解压后的插件源码目录。
- `reports/{slug}.fetch.json`：单个插件 fetch report。
- `reports/summary.json`：本次下载汇总和审计 handoff。

## Handoff 字段

脚本会在 JSON 中生成类似结构：

```json
{
  "skill": "php-audit-pipeline",
  "framework_skill": "php-wordpress-audit",
  "source_path": "./wp-audit-runs/plugins/example/example",
  "output_path": "./wp-audit-runs/audit/example",
  "fetch_report": "./wp-audit-runs/reports/example.fetch.json"
}
```

含义：

- `skill`：后续应调用的审计流水线。
- `framework_skill`：WordPress 专项审计提示。
- `source_path`：解压后的插件源码目录，审计目标应指向这里。
- `output_path`：建议的审计报告输出目录。
- `fetch_report`：下载和解压元数据，仅用于上下文，不是漏洞证据。

## 推荐审计流程

1. 使用 `wp-plugin-audit-hunter` 搜索并下载插件。
2. 从 `reports/summary.json` 读取 `audit_handoff`。
3. 使用 `php-audit-pipeline` 审计 `source_path`。
4. 在流水线中调用 `php-wordpress-audit` 做 WordPress hook、AJAX、nonce、capability、SQL、XSS、上传、SSRF 等专项检查。
5. 由 `php-audit-pipeline` 负责误报过滤、可达性分析、严重性评估和最终报告。

## 安全说明

本项目只面向授权的本地源码审计。不要用它扫描或攻击未授权的线上站点。

如果要做真实漏洞确认，应在受控测试环境里完成，并由 `php-audit-pipeline` 输出证据链和修复建议。

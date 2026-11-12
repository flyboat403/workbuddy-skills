# Changelog

## Local upgrade (2026-11-09)

- Upgraded from v2.0.1 to ClawHub **v2.1.3** (published 2026-04-11).
- Kept the locally expanded reference guides as
  `references/local-advanced-search.md` and `references/local-international-search.md`.
  They were written against the v2.0.1 engine list (17 engines, including Toutiao and
  Jisilu); the v2.1.3 list has 16 engines and uses Shenma instead. The official reference
  files stay at their original paths and are the ones linked from SKILL.md.
- Upstream package metadata is inconsistent: `_meta.json` still says 2.0.1,
  `metadata.json` says 2.1.0, and this changelog stops at v2.1.0. The authoritative
  installed version is recorded in `.clawhub/origin.json`.
- Pre-upgrade v2.0.1 snapshot:
  `~/.workbuddy-ai/_skill_backups/multi-search-engine-v2.0.1-before-upgrade-20261109/`

## v2.1.0 (2026-04-11)
- Version bump to 2.1.0

## v2.0.1 (2026-02-06)
- Simplified documentation
- Removed gov-related content
- Optimized for ClawHub publishing

## v2.0.0 (2026-02-06)
- Added 9 international search engines
- Enhanced advanced search capabilities
- Added DuckDuckGo Bangs support
- Added WolframAlpha knowledge queries

## v1.0.0 (2026-02-04)
- Initial release with 8 domestic search engines

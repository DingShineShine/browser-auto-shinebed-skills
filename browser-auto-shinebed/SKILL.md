---
name: browser-auto-shinebed
description: "Install the Shinebed AdsPower bridge wrapper for browser-act. Use when a user mentions AdsPower, ADS browser, multi-store browser automation, browser-act AdsPower mode, adspower user ids, browser-act bridge, reusable workflow skills, browser-act skill forge, or Forge Mode."
metadata:
  author: Shinebed
  version: "0.1.7"
  install: "uv tool install browser-auto-shinebed --python 3.12"
  homepage: "https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/browser-auto-shinebed"
  requires:
    runtime: "Python 3.12, uv package manager, AdsPower Local API when using adspower user ids"
---

# browser-auto-shinebed

This public Skill installs the Shinebed AdsPower bridge wrapper and carries the
Forge Mode references used to create reusable browser-act workflow Skills.

## Start Here

Install or upgrade the CLI package:

```bash
uv tool install --force browser-auto-shinebed --python 3.12
```

Verify the wrapper:

```bash
browser-act doctor
```

Then load the wrapper guide from the installed CLI:

```bash
browser-act get-skills browser-auto-shinebed --skill-version 0.1.6
```

Use the CLI guide for wrapper verification, AdsPower browser mode, and command
compatibility. Forge Mode instructions live in this Git-installed Skill under
`references/`; do not rely on CLI output as the Forge source of truth.

## Forge Mode

Use Forge Mode when the user asks to create, forge, build, or update a reusable
Skill for a browser-act site workflow, including extraction, batch scraping,
repeated operations, monitoring, exports, submissions, or "do this every day"
style tasks.

Before doing Forge work, read the relevant reference files from this Skill:

- For data extraction, scraping, pagination, network capture, or DOM extraction:
  read [references/forge-extraction.md](references/forge-extraction.md).
- For submissions, exports, form fills, report generation, settings changes, or
  other externally visible operations: read
  [references/forge-operation.md](references/forge-operation.md).
- Before generating the reusable Skill package: read
  [references/forge-output-template.md](references/forge-output-template.md).

If this Skill was installed without `references/`, pull the public references
from GitHub before attempting Forge work:

```bash
git clone --depth 1 https://github.com/DingShineShine/browser-auto-shinebed-skills tmp/browser-auto-shinebed-skills
```

Then read:

```text
tmp/browser-auto-shinebed-skills/browser-auto-shinebed/references/forge-extraction.md
tmp/browser-auto-shinebed-skills/browser-auto-shinebed/references/forge-operation.md
tmp/browser-auto-shinebed-skills/browser-auto-shinebed/references/forge-output-template.md
```

Forge output must still use normal `browser-act` commands. If the workflow runs
inside an AdsPower profile, open the session with `adspower:<user_id>` first,
then perform exploration and generated Skill execution through the wrapper.

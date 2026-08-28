# browser-auto-shinebed-skills

Public discovery Skill for installing the Shinebed AdsPower bridge wrapper for `browser-act`.

This repository is intentionally thin. It contains only the installable Skill stub that points agents to the published `browser-auto-shinebed` CLI package. The full implementation stays in the private development repository, and the CLI serves the full agent guide that matches the installed package version.

## Install

Tell your AI agent:

```text
Install browser-auto-shinebed.
Skill source:
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/browser-auto-shinebed

After installation, verify the wrapper and load the full guide from the installed CLI.
```

## What the Skill Does

The public Skill asks the agent to run:

```bash
uv tool install --force browser-auto-shinebed --python 3.12
browser-act doctor
browser-act get-skills browser-auto-shinebed --skill-version 0.1.5
```

`browser-act get-skills browser-auto-shinebed` prints the complete AdsPower and Forge Mode instructions from the installed package, so the guide stays aligned with the CLI version.

## Repository Contents

```text
README.md
browser-auto-shinebed/SKILL.md
.gitignore
```

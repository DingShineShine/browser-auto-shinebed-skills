# browser-auto-shinebed-skills

Public discovery Skill for installing the Shinebed AdsPower bridge wrapper for `browser-act`.

This repository is intentionally thin. It contains the installable Skill entrypoint and Forge Mode reference docs, but not the Python implementation, tests, reports, screenshots, generated Skills, or development artifacts. The full implementation stays in the private development repository.

## Install

Tell your AI agent:

```text
Install browser-auto-shinebed.
Skill source:
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/browser-auto-shinebed

After installation, verify the wrapper and read the Forge references from the installed Skill.
```

## What the Skill Does

The public Skill asks the agent to install and verify the wrapper:

```bash
uv tool install --force browser-auto-shinebed --python 3.12
browser-act doctor
browser-act get-skills browser-auto-shinebed --skill-version 0.1.6
```

`browser-act get-skills browser-auto-shinebed` prints wrapper and AdsPower command guidance from the installed package. Forge Mode is guided by the public Git Skill references in `browser-auto-shinebed/references/`.

For Forge work, the agent reads:

```text
browser-auto-shinebed/references/forge-extraction.md
browser-auto-shinebed/references/forge-operation.md
browser-auto-shinebed/references/forge-output-template.md
```

If an environment only has the CLI package and not the Git-installed Skill, pull this repository and read those reference files before forging reusable Skills:

```bash
git clone --depth 1 https://github.com/DingShineShine/browser-auto-shinebed-skills tmp/browser-auto-shinebed-skills
```

## Repository Contents

```text
README.md
browser-auto-shinebed/SKILL.md
browser-auto-shinebed/references/forge-extraction.md
browser-auto-shinebed/references/forge-operation.md
browser-auto-shinebed/references/forge-output-template.md
.gitignore
```

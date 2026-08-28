# browser-auto-shinebed-skills

Public Codex Skills for the Shinebed `browser-act` wrapper and reusable browser
automation workflows.

This repository is intentionally thin. It contains installable Skill entrypoints,
Forge Mode reference docs, and selected public workflow Skills, but not the
Python implementation, tests, reports, screenshots, downloaded files, private
upload flows, or development artifacts. The full implementation stays in the
private development repository.

## Available Skills

| Skill | Purpose | Install URL |
| --- | --- | --- |
| `browser-auto-shinebed` | Installs and verifies the AdsPower bridge wrapper for `browser-act`; includes Forge references. | `https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/browser-auto-shinebed` |
| `costco-product-reviews-scrape` | Scrapes public Costco product reviews through browser-act chrome mode and Bazaarvoice. | `https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/costco-product-reviews-scrape` |
| `chewy-product-reviews-scrape` | Scrapes public Chewy product reviews through browser-act chrome mode and Chewy GraphQL. | `https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/chewy-product-reviews-scrape` |
| `tiktok-video-comments-scrape` | Scrapes TikTok video comments and replies through browser-act chrome-direct mode and TikTok web comment APIs. | `https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/tiktok-video-comments-scrape` |

## User Install Flow

Tell your AI agent:

```text
Install browser-auto-shinebed.
Skill source:
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/browser-auto-shinebed

After installation, verify the wrapper and read the Forge references from the installed Skill.
```

Then install one workflow Skill:

```text
Install Costco product reviews scraping:
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/costco-product-reviews-scrape
```

or:

```text
Install Chewy product reviews scraping:
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/chewy-product-reviews-scrape
```

or:

```text
Install TikTok video comments scraping:
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/tiktok-video-comments-scrape
```

Start a new task or next turn after installation, then ask naturally:

```text
Scrape all Costco reviews for this product and save the result as JSON:
https://www.costco.com/...
```

or:

```text
Scrape all comments and replies for this TikTok video and save the result as JSON:
https://www.tiktok.com/@.../video/...
```

If a Skill is already installed, ask the agent to replace the local Skill folder
with the latest GitHub version and install again from the same URL.

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
costco-product-reviews-scrape/SKILL.md
costco-product-reviews-scrape/scripts/scrape-reviews.py
costco-product-reviews-scrape/scripts/inspect-costco-review-page.py
chewy-product-reviews-scrape/SKILL.md
chewy-product-reviews-scrape/scripts/scrape-reviews.py
tiktok-video-comments-scrape/SKILL.md
tiktok-video-comments-scrape/scripts/scrape-comments.py
.gitignore
```

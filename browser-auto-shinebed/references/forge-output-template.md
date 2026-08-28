# Forge Output Template

Read this file before generating a reusable Skill in Forge Mode.

## Directory Layout

Generate each capability package under:

```text
output/{skill-name}/{capability-name}/
|-- SKILL.md
`-- scripts/
    `-- {script-name}.py
```

The `output` directory is only the authoring location. Command snippets inside the generated `SKILL.md` must be portable after installation: reference helper scripts from the Skill root as `python scripts/{script-name}.py`, never with an absolute workspace path or any generated-package parent directory before `scripts/`.

Naming rules:

- Use lowercase English kebab-case for skill names, capability names, and script filenames.
- Use only letters, digits, and hyphens.
- Keep generated Skill descriptions in English for reliable matching.

## Generated SKILL.md Shape

```markdown
---
name: {site-capability-name}
description: "{Site first, then capability, inputs, outputs, and trigger phrases. English only.}"
---

# {Site} - {Capability}

## Language

Reply in the user's language.

## Objective

{One sentence describing what this Skill does.}

## Prerequisites

- Target page: `{url}`
- Login or account state: {required/not required and visible confirmation}

## Pre-Execution Checks

1. Confirm `browser-act` is available.
2. Confirm the target page is open or navigate to it.
3. Confirm required login state before execution.

## Capability Components

### API: {component}

Command:

```bash
eval "$(python scripts/{script-name}.py --param value)"
```

Parameters:

- `--param`: {business meaning}

Output:

```json
{
  "field": "example"
}
```

### Network Capture: {component}

1. `navigate {url-or-url-pattern}`
2. `wait stable`
3. `network requests --type xhr,fetch --filter {endpoint-keyword}`
4. `network request <id>`

Endpoint characteristic: `{stable URL substring}`

### DOM: {component}

Command:

```bash
eval "$(python scripts/{script-name}.py --param value)"
```

### AI Workflow: {component}

Use browser-act subcommands and visual descriptions only. Do not include CSS selectors in AI workflow steps.

1. `state` locate {visual element description} -> `click <index>`
2. `wait stable`
3. `get markdown` and extract {fields}

## Enum Parameters

Document option discovery methods. Use `[API]`, `[DOM]`, and `[AI]` labels. Mark unavailable collections as `[collection failed]`.

## Pagination

Document only the verified pagination type: API, URL, DOM, or AI.

## Success Criteria

Use quantifiable criteria such as result count, required field completeness, response status, or visible success confirmation.

## Known Limitations

Only list limitations observed during exploration.

## Experience Notes

Path: `{working-directory}/browser-act-skill-forge-memories/{skill-name}-{capability-name}.memory.md`

Read the file before execution if it exists. Append only unexpected execution discoveries, not task results.
```

Delete unused component sections from the generated Skill. Do not leave template placeholders.

## Python Script Template

Each `scripts/*.py` file should only assemble and print browser-side JavaScript for `browser-act eval`.

```python
import argparse
import json
import sys


def js_string(value: str) -> str:
    return json.dumps(value)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--param", required=True)
    args = parser.parse_args()

    js = f"""
    (() => {{
      try {{
        const param = {js_string(args.param)};
        return JSON.stringify({{ ok: true, param }});
      }} catch (error) {{
        return JSON.stringify({{ error: true, message: String(error && error.message || error) }});
      }}
    }})()
    """
    print(js)


if __name__ == "__main__":
    main()
```

## Output Requirements

- All generated commands must use normal browser-act subcommands.
- Generated command snippets must be install-relative. Use `python scripts/{script-name}.py` for helper scripts so the Skill works after being copied into a user Skill directory.
- Python files must not make network requests, read/write task data, or call browser-act.
- Browser-side JavaScript must wrap errors and return `{"error": true, "message": "..."}` on structural failure.
- Use business parameter names such as `keyword`, `page`, `date-range`, or `status`; do not expose selectors as user parameters.
- Do not include real customer data, credentials, AdsPower profile ids, or one-off exploration inputs.
- Do not mention source scraper products or competitor tools in generated Skill names or descriptions.
- Include enough output examples for future agents to understand the data shape.

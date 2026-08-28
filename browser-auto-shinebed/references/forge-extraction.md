# Forge Extraction Reference

Read this file before exploring an extraction capability in Forge Mode.

## Goal

Find a stable way to obtain the requested data from the target site through the user's browser session. Prefer structured data paths first, then DOM extraction, then an AI workflow when the page cannot be made scriptable.

## Decision Order

1. Open the target page and run `wait stable`.
2. Inspect page traffic with `network requests --type xhr,fetch --filter {domain-or-endpoint-keyword}`.
3. If a response contains the target data, inspect it with `network request <id>`.
4. If the request is transparent and reproducible, verify it with one `eval` fetch call.
5. If the request needs site-generated signatures, tokens, or body structures, use UI operations to trigger it and read the response through network capture.
6. If no usable network path exists, extract from DOM with verified selectors.
7. If selectors or scripts cannot stably cover the task, write an AI workflow using browser-act subcommands and visual descriptions.

## API Verification

Use one browser-side `eval` to verify the endpoint. Return a compact JSON summary: count, total if available, and a sample item. Verify that the returned data matches the visible page and that changed parameters produce changed results.

For list data, verify pagination:

- Page-number pagination: request page 1 and page 2, confirm first item differs.
- Cursor pagination: read the next cursor from response 1, request response 2.
- URL pagination: navigate to the next page URL and rerun extraction.
- DOM pagination: click or scroll, wait stable, rerun extraction.

## UI Trigger + Network Capture

Use this path when the site can produce structured data but the request cannot be independently reconstructed.

1. Record the current page URL and the target request characteristics.
2. Inject business parameters through URL navigation or UI controls.
3. Use `network har start` when an interaction-specific request needs to be isolated.
4. Trigger the request.
5. Run `wait stable`.
6. Read `network requests` and `network request <id>`.
7. Record endpoint characteristics, parameter injection method, response fields, and error signals.

## DOM Extraction

Before selector extraction, check for embedded structured data in the page HTML or framework state. If unavailable, batch-test candidate selectors in one `eval` call and return match counts plus short samples.

Selector priority:

1. `data-testid`
2. `id`
3. `name`
4. `aria-label`
5. stable structural selectors

Avoid pure positional selectors unless the structure is demonstrably stable. Re-test selectors after refresh or navigation when possible.

## Enum Parameters

For dropdowns, radio groups, filters, category selectors, and similar controls, record how to obtain current options instead of hardcoding observed values.

Priority:

1. API endpoint returning options.
2. DOM option extraction.
3. AI visual interaction steps.

For cascading controls, record dependency order such as `country -> state -> city`. Mark failed enum collection as `[collection failed]` and continue.

## Exploration Constraints

- Every browser roundtrip should produce new information.
- Batch selector tests and UI control scans into single `eval` calls.
- Do not override `window.fetch`, `XMLHttpRequest`, or site network APIs.
- Use `network requests --filter` for normal filtering; clear traffic only before a deliberate navigation/reload.
- Do not call third-party scraping services or official open-platform APIs that require separate developer credentials.
- Data access must remain within what the user can manually view in the browser.

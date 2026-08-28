# Forge Operation Reference

Read this file before exploring an operation or submission capability in Forge Mode.

## Goal

Capture how a user-visible operation is performed, identify required parameters, and generate a reusable browser-act workflow with controlled side effects. Operations include form submission, report generation, export actions, account settings changes, and other site actions.

## Safety Protocol

When exploring a write operation, capture request intent without completing the operation whenever possible:

1. Navigate to the target page and run `wait stable`.
2. Start capture with `network har start`.
3. Turn offline mode on with `network offline on`.
4. Fill required controls.
5. Trigger the submit/export/generate action.
6. Wait one or two seconds for frontend handlers to fire.
7. Stop capture with `network har stop tmp/{operation-name}.har`.
8. Turn online mode off with `network offline off`.
9. Immediately navigate away or reset the page to prevent retries.

Use the HAR to record endpoint URL, method, request body structure, and the input values that caused the request.

## Feasibility Decision

Choose the generated strategy after inspecting the captured request:

- API strategy: request fields are transparent, parameterizable, and free of opaque signatures or short-lived tokens.
- DOM strategy: the page must generate credentials, signatures, or body structures, so generated scripts only fill controls and trigger the native UI.
- AI workflow: controls require visual judgment, captcha/manual confirmation, or dynamic interactions that cannot be made stable with scripts.

## Control Discovery

Prefer a batch `eval` scan over one-by-one inspection. Capture tag, type, name, id, placeholder, current value, checked state, labels, and select options.

For framework inputs, fill through native setters and dispatch `input` and `change` events:

```javascript
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
const el = document.querySelector('{selector}');
setter.call(el, '{value}');
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

For dynamic dropdowns, first try DOM/API option discovery. If that fails, document the AI interaction step with visual descriptions only.

## Generated Operation Skill

Record enough detail for future execution:

- Preconditions: target page URL, login requirement, visible page state.
- Parameters: business names, required/optional status, default values.
- Atomic components: fill fields, select options, submit, read result, download/export confirmation.
- Verification signals: success toast, request status, generated file entry, URL change, or visible confirmation text.
- Failure handling: missing control, permission limitation, timeout, duplicate request risk.

## Operation Constraints

- Never perform destructive or externally visible actions during exploration unless the user explicitly asked and confirmed.
- Generated scripts may assemble JavaScript for `browser-act eval`, but should not call browser-act themselves.
- Do not store credentials, real customer data, AdsPower profile ids, or one-off task inputs in generated Skills.
- If an operation cannot be safely tested, produce an AI workflow plus clear manual verification steps instead of pretending it is fully automated.

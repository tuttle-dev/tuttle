# Dialog / Modal Scroll Safety

Every dialog or modal MUST be viewport-safe:

1. Outer container: `max-h-[85vh] flex flex-col overflow-hidden`
2. Header / footer: add `shrink-0` so they never collapse
3. Body / content area: `flex-1 overflow-y-auto`

If a single pane has more than ~6 form fields, split it into multiple wizard steps or tabs instead of a long scrollable form.

```tsx
// BAD — no max-h, body can overflow off-screen
<div className="bg-bg-sidebar rounded-xl">
  <div className="px-5 py-4">{/* header */}</div>
  <div>{/* body with many fields */}</div>
</div>

// GOOD — viewport-capped, scrollable body
<div className="bg-bg-sidebar rounded-xl max-h-[85vh] flex flex-col overflow-hidden">
  <div className="px-5 py-4 shrink-0">{/* header */}</div>
  <div className="flex-1 overflow-y-auto">{/* body */}</div>
</div>
```

Applies to all `.tsx` files that render dialogs or modals.

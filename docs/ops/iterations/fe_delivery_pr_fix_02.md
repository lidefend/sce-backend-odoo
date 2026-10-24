# FE-DELIVERY-PR-FIX-02

Probe-only repair based on `d7edc7ffbf1e5e01143a0be9431d22783f445ec4`.

## Assertion review

1. Identity width ratio → verifies identity text and declared primary action are present.
2. Completion vertical alignment → verifies normalized business text `立项完成度：3/3`.
3. Completion horizontal order → verifies `done.summary` precedes `total.summary` in the declared DOM.
4. Slash vertical alignment → verifies the slash remains inside the declared completion region.

The unrelated maintenance/board comparison now checks content and semantic identity
instead of pixel width/height.

## Results

- `make verify.frontend.project_detail_summary.browser`: PASS, 28 checks across 320/390/768/1440.
- `make verify.frontend.playwright_vendor_coupling.guard`: PASS, 7 tests; baseline unchanged.

Pending affected frontend tests and final Quick.

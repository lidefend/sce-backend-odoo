# Scheduled CI retained-detail performance repair

Status: active

The full frontend release gate on main `758a01e4df63a5ec0cb43c00cd02b463d01962b3`
run `42629977654` reached runtime evidence successfully:

- page identity: 89/89 surfaces, 0 failures
- runtime navigation observation: finance 28, project member 17, PM 31, owner 13, all PASS
- role release projection and fixture setup: PASS

It then failed only at the performance probe:

```text
payment_detail: warmed retained detail page reloaded its primary contract 15 time(s)
```

The probe performs a full `page.goto('/')` before every detail sample. That
destroys the warmed SPA document by definition. The same probe then requires the
in-memory detail contract cache to survive the reload, so its two assumptions
contradict each other. The failure is classified as a `validation_tool_defect`.

The repair keeps the cold role-home measurement for `my_work`, while detail
scenarios return to `/my-work` through browser history inside the same SPA
document. The retained-detail contract request assertion then measures the
intended warmed navigation instead of a full application reload.

No frontend product behavior, route, ACL, contract, fixture, database or
deployment state is changed.

Validation at baseline `daa158808e380db0cae4a484e3fcb3adf359d66c` plus the
explicit P4 dirty scope:

- `verify.frontend.delivery_hardening.guard`: 17 tests, PASS
- `verify.frontend.standard_preview.unit`: 173 tests, PASS
- `verify.agent.resume.unit`: 56 tests, PASS
- `verify.agent.ledger.unit`: 18 tests plus ledger guard, PASS

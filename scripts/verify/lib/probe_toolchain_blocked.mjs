// This is deliberately the first dependency of a blocked ESM entrypoint.
// Throw during module evaluation, before any later dependency or main body runs.
throw new Error('PROBE_TOOL_UNSUPPORTED: legacy probe requires namespace-contract adaptation; see config/frontend/probe_toolchain_registry.json. No runtime coverage was produced.');

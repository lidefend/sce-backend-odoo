#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend/apps/web/src"


def require(path: str, *markers: str) -> str:
    source = (ROOT / path).read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL {path}: missing {missing}")
    return source


def forbid(path: str, *markers: str) -> None:
    source = (ROOT / path).read_text(encoding="utf-8")
    found = [marker for marker in markers if marker in source]
    if found:
        raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL {path}: forbidden {found}")


require(
    "frontend/apps/web/src/app/contextEpoch.ts",
    "beginContextTransition",
    "isCurrentContextEpoch",
    "invalidateContextRequests",
    "currentContextSignal",
    "AbortController",
)
require(
    "frontend/apps/web/src/stores/session.ts",
    "beginContextTransition",
    "isCurrentContextEpoch",
    "invalidateContextRequests",
)
require(
    "frontend/apps/web/src/views/MyWorkView.vue",
    "currentContextEpoch",
    "isCurrentContextEpoch",
    "if (!session.token)",
)
require(
    "frontend/apps/web/src/app/productErrorState.ts",
    "登录已失效",
    "无权访问",
    "记录不存在",
    "数据已发生变化",
    "网络连接异常",
    "服务暂时不可用",
    "TECHNICAL_TEXT",
)
require(
    "frontend/apps/web/src/components/StatusPanel.vue",
    "resolveProductErrorState",
    "aria-live",
    "aria-busy",
    "正在重试",
)
require(
    "frontend/apps/web/src/components/business/IntentConfirmationDialog.vue",
    "<dialog",
    "showModal()",
    "@cancel.prevent",
    "trigger?.focus()",
)
require(
    "frontend/apps/web/src/layouts/AppShell.vue",
    "skip-link",
    'id="main-content"',
    'aria-label="主导航"',
)
app_shell = require(
    "frontend/apps/web/src/layouts/AppShell.vue",
    'id="primary-sidebar"',
    'v-if="sidebarVisible"',
    'aria-controls="primary-sidebar"',
    ':aria-expanded="sidebarVisible"',
    "mobileViewport.value ? mobileSidebarOpen.value : !sidebarHidden.value",
    "event.key !== 'Escape'",
    "sidebarToggleButton.value?.focus()",
)
toggle_match = re.search(
    r"<button\b(?=[^>]*\baria-controls=\"primary-sidebar\")"
    r"(?=[^>]*:aria-expanded=\"sidebarVisible\")[^>]*>",
    app_shell,
    re.DOTALL,
)
if not toggle_match:
    raise SystemExit(
        "[frontend_delivery_hardening_guard] FAIL AppShell sidebar toggle must control "
        "primary-sidebar with the unified sidebarVisible state"
    )
client = require("frontend/apps/web/src/api/client.ts", "reason=session_expired")
require("frontend/apps/web/src/api/client.ts", "currentContextSignal()")
if "redirect=${encodeURIComponent" in client:
    raise SystemExit("[frontend_delivery_hardening_guard] FAIL 401 may restore a sensitive route")
forbid("frontend/apps/web/src/stores/session.ts", "token_prefix", "token.slice(")
require("frontend/apps/web/package.json", '"@axe-core/playwright": "4.10.2"')
require(
    "scripts/verify/frontend_delivery_hardening_browser.mjs",
    "DELIVERY_HARDENING_PERF_ONLY",
    "DELIVERY_HARDENING_SKIP_PERF",
    "company_switch_warmup_runs",
    "governed company-switch warm-up count",
    "isolated performance evidence SHA mismatch",
    "fs.writeFileSync(path.join(OUT, 'performance.json')",
)
performance_policy = json.loads(
    (ROOT / "config/frontend/release_performance_budgets_v1.json").read_text(encoding="utf-8")
)
company_switch_warmup_runs = performance_policy.get("company_switch_warmup_runs")
minimum_sample_count = performance_policy.get("minimum_sample_count")
if (
    not isinstance(company_switch_warmup_runs, int)
    or not isinstance(minimum_sample_count, int)
    or company_switch_warmup_runs < minimum_sample_count
):
    raise SystemExit(
        "[frontend_delivery_hardening_guard] FAIL governed company-switch warm-up "
        "count must cover at least the measured sample count"
    )
baseline_path = ROOT / str(performance_policy.get("relative_baseline_path") or "")
if not baseline_path.is_file():
    raise SystemExit("[frontend_delivery_hardening_guard] FAIL governed performance baseline is missing")
performance_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
required_baseline_scenarios = set((performance_policy.get("scenarios") or {}).keys())
actual_baseline_scenarios = set((performance_baseline.get("scenarios") or {}).keys())
if actual_baseline_scenarios != required_baseline_scenarios:
    missing = sorted(required_baseline_scenarios - actual_baseline_scenarios)
    unexpected = sorted(actual_baseline_scenarios - required_baseline_scenarios)
    raise SystemExit(
        "[frontend_delivery_hardening_guard] FAIL governed performance baseline scenario mismatch "
        f"missing={missing} unexpected={unexpected}"
    )
if int(performance_baseline.get("runs_per_scenario") or 0) < minimum_sample_count:
    raise SystemExit("[frontend_delivery_hardening_guard] FAIL governed performance baseline sample count is too small")
if int(performance_baseline.get("company_switch_warmup_runs") or 0) != company_switch_warmup_runs:
    raise SystemExit("[frontend_delivery_hardening_guard] FAIL governed company-switch baseline warm-up count mismatch")
for scenario, metrics in (performance_baseline.get("scenarios") or {}).items():
    samples = metrics.get("samples_ms") or []
    if len(samples) < minimum_sample_count or not all(isinstance(value, (int, float)) and value >= 0 for value in samples):
        raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL invalid baseline samples scenario={scenario}")
    if not all(isinstance(metrics.get(name), (int, float)) for name in ("median_ms", "p95_ms", "max_ms")):
        raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL incomplete baseline metrics scenario={scenario}")
for field in ("git_sha", "captured_at", "database", "environment", "source"):
    if not performance_baseline.get(field):
        raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL governed performance baseline missing {field}")
if not re.fullmatch(r"[0-9a-f]{40}", str(performance_baseline.get("git_sha") or "")):
    raise SystemExit("[frontend_delivery_hardening_guard] FAIL governed performance baseline git_sha must be full length")
require(
    "make/runtime_ops.mk",
    "DELIVERY_HARDENING_PERF_ONLY=1",
    "DELIVERY_HARDENING_SKIP_PERF=1",
)
require(
    "frontend/apps/web/src/api/contract.ts",
    "CREATE_CONTRACT_CACHE_TTL_MS",
    "currentContextEpoch()",
    "options?.renderProfile === 'create'",
    "!Number(options?.recordId || 0)",
)

delivery_hardening_browser = require(
    "scripts/verify/frontend_delivery_hardening_browser.mjs",
    "performanceReport.scenarios.company_switch = stats(switchSamples);",
    "[verify.frontend.delivery_hardening.performance_baseline] CAPTURED",
)
if delivery_hardening_browser.index("performanceReport.scenarios.company_switch = stats(switchSamples);") > delivery_hardening_browser.index("[verify.frontend.delivery_hardening.performance_baseline] CAPTURED"):
    raise SystemExit("[frontend_delivery_hardening_guard] FAIL baseline capture must include company-switch samples")

diff = subprocess.run(
    ["git", "diff", "--unified=0", "origin/main", "--", "frontend/apps/web/src"],
    cwd=ROOT,
    check=True,
    capture_output=True,
    text=True,
).stdout
added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
for label, pattern in {
    "hard-coded color": r"#[0-9a-fA-F]{3,8}\b|rgba?\(",
    "page inline style": r"\sstyle=\"",
    "model-specific CSS": r"\.(?:project|contract|settlement|payment)[-_][\w-]+\s*\{",
}.items():
    if re.search(pattern, added):
        raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL new {label}")

writers = []
for path in SRC.rglob("*"):
    if path.suffix not in {".ts", ".vue"}:
        continue
    source = path.read_text(encoding="utf-8")
    if "document.title" in source.replace("previewWindow.document.title", ""):
        writers.append(path.relative_to(SRC).as_posix())
if writers != ["App.vue"]:
    raise SystemExit(f"[frontend_delivery_hardening_guard] FAIL document.title writers={writers}")

print("[frontend_delivery_hardening_guard] PASS error_states=12 title_writers=1 async_epoch=enabled axe=4.10.2")

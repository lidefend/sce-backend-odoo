#!/usr/bin/env python3
"""G3.2 BOQ 导入预检快照只读投影前端守卫。

校验三件套（API 封装 / presentation Model / 只读面板组件）与单测的
契约准入标记：
- API 封装必须走专用 intent（project.boq.import.preview.fetch），
  不得绕过 intent 直接调用通用 data 通道；
- Model 必须实现四态视图状态机（ready / missing_payload /
  error / degraded_shape）与只读标记；
- 组件必须按状态渲染错误态/空态（safe_degradation 语义，不白屏），
  且不得包含任何写操作入口；
- 单测必须覆盖四态投影。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

API_PATH = "frontend/apps/web/src/api/boqImportPreview.ts"
MODEL_PATH = "frontend/apps/web/src/app/presentation/boqImportPreview.ts"
COMPONENT_PATH = "frontend/apps/web/src/components/boq/BoqImportPreviewPanel.vue"
TEST_PATH = "frontend/apps/web/scripts/boq_import_preview_model_test.ts"


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate() -> list[str]:
    failures: list[str] = []

    api = source(API_PATH)
    model = source(MODEL_PATH)
    component = source(COMPONENT_PATH)
    test = source(TEST_PATH)

    # ── API 封装：契约准入标记 ──────────────────────────────
    for marker in (
        "BOQ_IMPORT_PREVIEW_FETCH_INTENT = 'project.boq.import.preview.fetch'",
        "BOQ_IMPORT_PREVIEW_SCHEMA = 'sc.boq.import.preview.v1'",
        "fetchBoqImportPreview",
        "safe_degradation",
        "intentRequest",
    ):
        if marker not in api:
            failures.append(f"boq import preview api missing {marker}")
    # 只读投影不得绕过专用 intent 走通用 data 通道
    for forbidden in ("op: 'list'", "op: 'create'", "op: 'write'", "op: 'unlink'", "op: 'read'"):
        if forbidden in api:
            failures.append(f"boq import preview api must not use generic data op: {forbidden}")

    # ── Model：四态状态机 + 只读标记 ────────────────────────
    for marker in (
        "BOQ_IMPORT_PREVIEW_VIEW_READONLY = true",
        "BOQ_IMPORT_PREVIEW_STATE_READY = 'ready'",
        "BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD = 'missing_payload'",
        "BOQ_IMPORT_PREVIEW_STATE_ERROR = 'error'",
        "BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE = 'degraded_shape'",
        "projectBoqImportPreview",
        "BATCH_NOT_FOUND",
        "MISSING_PARAMS",
        "sc.boq.import.preview.v1",
    ):
        if marker not in model:
            failures.append(f"boq import preview model missing {marker}")
    # Model 是纯投影：不得发起网络请求或会话访问
    for forbidden in ("fetch(", "intentRequest", "useSessionStore", "XMLHttpRequest"):
        if forbidden in model:
            failures.append(f"boq import preview model must stay pure: found {forbidden}")

    # ── 组件：状态化渲染 + 只读边界 ─────────────────────────
    for marker in (
        "data-boq-import-preview",
        ":data-view-state",
        'data-readonly="true"',
        "data-preview-error",
        "data-preview-empty",
        "data-preview-stats",
        "BoqImportPreviewViewModel",
    ):
        if marker not in component:
            failures.append(f"BoqImportPreviewPanel missing {marker}")
    if "v-if=\"model.viewState === 'error'\"" not in component:
        failures.append("BoqImportPreviewPanel must render a structured error state")
    if "model.viewState === 'missing_payload'" not in component:
        failures.append("BoqImportPreviewPanel must render missing_payload empty state")
    if "model.viewState === 'degraded_shape'" not in component:
        failures.append("BoqImportPreviewPanel must render degraded_shape defensive state")
    # 组件为只读投影：不得出现写操作或导入动作
    for forbidden in ("api.data", "action_import", "call_method", "@click", "op: 'create'"):
        if forbidden in component:
            failures.append(f"BoqImportPreviewPanel is readonly projection: found {forbidden}")

    # ── 单测：四态覆盖 ──────────────────────────────────────
    for marker in (
        "BOQ_IMPORT_PREVIEW_STATE_READY",
        "BOQ_IMPORT_PREVIEW_STATE_MISSING_PAYLOAD",
        "BOQ_IMPORT_PREVIEW_STATE_ERROR",
        "BOQ_IMPORT_PREVIEW_STATE_DEGRADED_SHAPE",
        "BATCH_NOT_FOUND",
        "MISSING_PARAMS",
        "projectBoqImportPreview",
        "formatBoqPreviewAmount",
    ):
        if marker not in test:
            failures.append(f"boq import preview model test missing {marker}")

    # ── Makefile：单测目标注册 ──────────────────────────────
    frontend_mk = source("make/frontend.mk")
    if "verify.frontend.boq_import_preview.unit" not in frontend_mk:
        failures.append("make/frontend.mk does not register verify.frontend.boq_import_preview.unit")
    if "boq_import_preview_model_test.ts" not in frontend_mk:
        failures.append("make/frontend.mk does not wire boq_import_preview_model_test.ts")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        raise SystemExit(1)
    print("[OK] frontend boq import preview readonly projection guard passed")
    return 0


if __name__ == "__main__":
    main()

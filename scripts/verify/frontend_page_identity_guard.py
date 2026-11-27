#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/apps/web/src"


def fail(message: str) -> None:
    raise SystemExit(f"[frontend_page_identity_guard] FAIL: {message}")


required = {
    "layouts/AppShell.vue": "usePageIdentityRuntime",
    "views/ActionView.vue": "usePublishedPageIdentity",
    "pages/ContractFormPage.vue": "usePublishedPageIdentity",
    "App.vue": "document.title",
    "views/AccessDeniedView.vue": "usePageIdentityRuntime",
    "views/NotFoundView.vue": "usePageIdentityRuntime",
}
for relative, marker in required.items():
    source = (FRONTEND / relative).read_text(encoding="utf-8")
    if marker not in source:
        fail(f"missing authoritative identity integration: {relative}:{marker}")

writers = []
for path in FRONTEND.rglob("*"):
    if path.suffix not in {".ts", ".vue"}:
        continue
    source = path.read_text(encoding="utf-8")
    page_title_writes = source.replace("previewWindow.document.title", "")
    if "document.title" in page_title_writes:
        writers.append(path.relative_to(FRONTEND).as_posix())
if writers != ["App.vue"]:
    fail(f"document.title must have one page writer, got {writers}")

identity_sources = "\n".join(
    path.read_text(encoding="utf-8")
    for path in sorted((FRONTEND / "app").glob("pageIdentity*.ts"))
)
for forbidden in ("project.project", "construction.contract", "payment.request", "settlement"):
    if forbidden in identity_sources:
        fail(f"model-specific identity rule forbidden: {forbidden}")
for forbidden in ("model ===", "model !==", "includes(model)", "switch (model)", "switch(model)"):
    if forbidden in identity_sources:
        fail(f"model-specific identity branch forbidden: {forbidden}")

router = (FRONTEND / "router/index.ts").read_text(encoding="utf-8")
if "`${model || '记录'} #${id || ''}`" in router:
    fail("router still exposes model #id title")
if "action: '业务动作'" in router:
    fail("route-name generic business action title remains")
if "resolveRouteContractTitle(name, pageContracts) || ROUTE_STATE_TITLE_FALLBACKS[name]" not in router:
    fail("route activity title must consume the page contract")
if "resolveRoutePageIdentity(to, session.menuTree, session.pageContracts)" not in router:
    fail("route page identity must consume the page contract")

route_identity = (FRONTEND / "app/pageIdentityRoute.ts").read_text(encoding="utf-8")
for forbidden in (
    "const configured: Record<string, string>",
    "'配置工作台'",
    "'菜单配置'",
    "'表单字段配置'",
    "'场景健康'",
    "'场景发布包'",
    "'使用分析'",
    "'产品发布'",
    "'导航异常'",
):
    if forbidden in route_identity:
        fail(f"hardcoded page title remains: {forbidden}")

identity_adapter = (FRONTEND / "app/pageIdentityAdapters.ts").read_text(encoding="utf-8")
if "legacyTitle" in identity_adapter:
    fail("page identity must not retain a legacy title fallback")

form_labels = (FRONTEND / "pages/contractForm/uiLabels.ts").read_text(encoding="utf-8")
if "`记录 #${params.recordId}`" in form_labels:
    fail("form subtitle still exposes record id")

print("[frontend_page_identity_guard] PASS writers=1 integrations=6")

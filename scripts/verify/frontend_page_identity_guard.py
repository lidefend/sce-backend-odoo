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

route_query = (FRONTEND / "app/routeQuery.ts").read_text(encoding="utf-8")
for forbidden in ("scene_key: key", "scene_label:"):
    if forbidden in route_query:
        fail(f"canonical scene URL reintroduced redundant identity: {forbidden}")
if "delete query.entry_title;" not in route_query:
    fail("entry presentation titles must not enter route queries")

navigation_context = (FRONTEND / "app/navigationContext.ts").read_text(encoding="utf-8")
for forbidden in ("'entry_title'", "'return_label'", "'scene'", "'scene_key'", "'scene_label'"):
    if forbidden in navigation_context:
        fail(f"presentation-only navigation query remains allowlisted: {forbidden}")

router_source = (FRONTEND / "router/index.ts").read_text(encoding="utf-8")
for forbidden in ("current_business_category_label", "default_business_category_label"):
    if forbidden in router_source:
        fail(f"activity route still carries a business-category label: {forbidden}")

for forbidden in ("to.query.scene_label", "to.query.scene_key"):
    if forbidden in router_source:
        fail(f"router still consumes duplicate scene identity: {forbidden}")

scene_view = (FRONTEND / "views/SceneView.vue").read_text(encoding="utf-8")
for forbidden in ("scene_key: sceneKey", "scene_label: sceneLabel", "queryLabel:"):
    if forbidden in scene_view:
        fail(f"scene route still writes or consumes display identity: {forbidden}")

action_view_source = (FRONTEND / "views/ActionView.vue").read_text(encoding="utf-8")
for forbidden in ("route.query.scene_label", "route.query.scene_key"):
    if forbidden in action_view_source:
        fail(f"action view still consumes duplicate scene identity: {forbidden}")

action_navigation = (FRONTEND / "app/action_runtime/useActionViewNavigationRuntime.ts").read_text(encoding="utf-8")
if "scene_label:" in action_navigation:
    fail("action target still propagates a scene display label")

activity_title = (FRONTEND / "app/activityPageTitle.ts").read_text(encoding="utf-8")
if "queryLabel" in activity_title:
    fail("activity titles must not consume route-carried labels")

for relative in ("app/businessScenarioNavigation.ts", "app/enterpriseSetupNavigation.ts"):
    source = (FRONTEND / relative).read_text(encoding="utf-8")
    if "return_label" in source:
        fail(f"return labels must be derived from identity: {relative}")

action_view = (FRONTEND / "views/ActionView.vue").read_text(encoding="utf-8")
if "resolveContextReturnHref(route.query" not in action_view or "返回${identity.title}" not in action_view:
    fail("action return label must derive from the declared return target identity")
if "route.query.return_label" in action_view:
    fail("action view must not consume a URL-provided return label")

form_labels = (FRONTEND / "pages/contractForm/uiLabels.ts").read_text(encoding="utf-8")
if "`记录 #${params.recordId}`" in form_labels:
    fail("form subtitle still exposes record id")

print("[frontend_page_identity_guard] PASS writers=1 integrations=6")

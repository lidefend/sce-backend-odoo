/** @odoo-module **/

import { buildDomainSections, buildMenuSections, normalizeMenus, parseActionId } from "../src/js/sc_sidebar";

QUnit.module("smart_construction_core.sidebar");

QUnit.test("parseActionId supports common formats", function (assert) {
  assert.strictEqual(parseActionId({ action: "ir.actions.act_window,448" }), 448);
  assert.strictEqual(parseActionId({ action: 12 }), 12);
  assert.strictEqual(parseActionId({ action: [34, "ir.actions.act_window"] }), 34);
  assert.strictEqual(parseActionId({ action: { id: 56 } }), 56);
  assert.strictEqual(parseActionId({ action: "invalid" }), null);
  assert.strictEqual(parseActionId({}), null);
});

QUnit.test("normalizeMenus unwraps root and menu_data", function (assert) {
  const root = { id: 1, children: [] };
  const wrapped = { root: { root } };
  assert.strictEqual(normalizeMenus(wrapped), root);

  let captured = null;
  const menuData = { 1: root };
  normalizeMenus({ menu_data: menuData }, (map) => (captured = map));
  assert.strictEqual(captured, menuData);
});

QUnit.test("buildMenuSections handles object children", function (assert) {
  const root = {
    id: 0,
    children: [
      { id: 1, name: "A", action: "ir.actions.act_window,10", children: [] },
      { id: 2, name: "B", children: [{ id: 3, name: "B1", action: "ir.actions.act_window,20" }] },
    ],
  };
  const sections = buildMenuSections(root, null);
  assert.strictEqual(sections.length, 2);
  assert.strictEqual(sections[0].actionId, 10);
  assert.strictEqual(sections[1].children.length, 1);
  assert.strictEqual(sections[1].children[0].actionId, 20);
});

QUnit.test("buildDomainSections derives one domain per native top-level menu", function (assert) {
  const sections = [
    { id: 1, name: "项目管理", xmlid: "smart_construction_core.menu_sc_project_center", sequence: 10, actionId: 100, children: [] },
    { id: 2, name: "合同管理", xmlid: "smart_construction_core.menu_sc_contract_center", sequence: 20, actionId: 200, children: [] },
  ];
  const domains = buildDomainSections(sections, null);
  assert.strictEqual(domains.length, 2);
  assert.strictEqual(domains[0].key, "smart_construction_core.menu_sc_project_center");
  assert.strictEqual(domains[0].name, "项目管理");
  assert.strictEqual(domains[0].icon, "P");
  assert.strictEqual(domains[0].sections.length, 1);
  assert.strictEqual(domains[0].sections[0].id, 1);
  assert.strictEqual(domains[1].key, "smart_construction_core.menu_sc_contract_center");
  assert.strictEqual(domains[1].icon, "C");
});

QUnit.test("buildDomainSections never fabricates an unknown default domain", function (assert) {
  const sections = [
    { id: 7, name: "未登记入口", xmlid: "smart_construction_core.menu_sc_unknown", sequence: 70, actionId: 700, children: [] },
  ];
  const domains = buildDomainSections(sections, null);
  assert.strictEqual(domains.length, 1);
  assert.strictEqual(domains[0].key, "smart_construction_core.menu_sc_unknown");
  assert.strictEqual(domains[0].icon, "");
});

QUnit.test("buildMenuSections handles id children via map", function (assert) {
  const menuMap = {
    1: { id: 1, name: "A", action: "ir.actions.act_window,10", children: [] },
    2: { id: 2, name: "B", children: [3] },
    3: { id: 3, name: "B1", action: "ir.actions.act_window,20", children: [] },
  };
  const root = { id: 0, children: [1, 2] };
  const sections = buildMenuSections(root, menuMap);
  assert.strictEqual(sections.length, 2);
  assert.strictEqual(sections[1].children.length, 1);
  assert.strictEqual(sections[1].children[0].actionId, 20);
});

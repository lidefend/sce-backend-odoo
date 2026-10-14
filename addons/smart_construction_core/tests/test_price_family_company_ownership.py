# -*- coding: utf-8 -*-
"""Company ownership of the P1 price libraries.

``sc.labor.price``, ``sc.equipment.price`` and ``sc.subcontract.price`` carry
commercial price facts.  Before this slice they declared no company at all and
their record rules scoped project membership only, so a price row of another
company stayed readable and writable for any internal user.

The company is not a second, independently editable fact: it is derived from
the owning project (``related="project_id.company_id", store=True``), exactly
like the sibling ``sc.material.price`` derives it from its catalogue.  That
removes the duplicate declaration and the tautological project/company
constraint.  These checks read model source and the record-rule XML, so the
boundary stays provable in the dependency-free inner loop without an Odoo
server.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL_ROOT = ROOT / "addons" / "smart_construction_core" / "models" / "core"
RULES = ROOT / "addons" / "smart_construction_core" / "security" / "sc_record_rules.xml"

PRICE_MODELS = {
    "sc.labor.price": "labor_management.py",
    "sc.equipment.price": "equipment_management.py",
    "sc.subcontract.price": "subcontract_management.py",
}
INTERNAL_RULES = {
    "sc.labor.price": "rule_sc_internal_labor_price",
    "sc.equipment.price": "rule_sc_internal_equipment_price",
    "sc.subcontract.price": "rule_sc_internal_subcontract_price",
}
SUPER_ADMIN_RULES = {
    "sc.labor.price": "rule_sc_super_admin_labor_price",
    "sc.equipment.price": "rule_sc_super_admin_equipment_price",
    "sc.subcontract.price": "rule_sc_super_admin_subcontract_price",
}

DERIVED_COMPANY = (
    'company_id = fields.Many2one("res.company", '
    'related="project_id.company_id", store=True, readonly=True, index=True)'
)


def _field_value(field):
    text = (field.text or "").strip()
    if text:
        return text
    return (field.get("eval") or "").strip()


def _rules_by_id():
    found = {}
    for record in ET.parse(RULES).getroot().iter("record"):
        if record.get("model") != "ir.rule":
            continue
        fields = {}
        for field in record.findall("field"):
            fields[field.get("name")] = _field_value(field)
        found[record.get("id")] = fields
    return found


def _price_class_source(filename, model):
    source = (MODEL_ROOT / filename).read_text(encoding="utf-8")
    start = source.find('_name = "%s"' % model)
    if start == -1:
        raise AssertionError("%s is not defined in %s" % (model, filename))
    body = source[start:]
    end = body.find("\nclass ")
    return body if end == -1 else body[:end]


def _company_declarations(class_source):
    return [
        line.strip()
        for line in class_source.splitlines()
        if line.strip().startswith("company_id")
    ]


class PriceModelDeclarationTests(unittest.TestCase):
    """The company is a single fact derived from the owning project."""

    def test_company_is_declared_once_as_a_derived_fact(self):
        for model, filename in PRICE_MODELS.items():
            with self.subTest(model=model):
                class_source = _price_class_source(filename, model)
                declarations = _company_declarations(class_source)
                self.assertEqual(declarations, [DERIVED_COMPANY])

    def test_company_is_not_independently_editable_or_defaulted(self):
        for model, filename in PRICE_MODELS.items():
            with self.subTest(model=model):
                declaration = _company_declarations(
                    _price_class_source(filename, model)
                )[0]
                self.assertIn("related=", declaration)
                self.assertIn("readonly=True", declaration)
                self.assertNotIn("default=", declaration)
                self.assertNotIn('ondelete=', declaration)

    def test_no_duplicate_project_company_constraint(self):
        for model, filename in PRICE_MODELS.items():
            with self.subTest(model=model):
                class_source = _price_class_source(filename, model)
                self.assertNotIn("def _check_project_company(", class_source)
                self.assertNotIn(
                    '@api.constrains("company_id", "project_id")', class_source
                )


class PriceRecordRuleTests(unittest.TestCase):
    """The price rules keep the company boundary of the material sibling."""

    def setUp(self):
        self.rules = _rules_by_id()

    def test_internal_price_rule_carries_the_company_clause(self):
        for model, rule_id in INTERNAL_RULES.items():
            with self.subTest(model=model):
                self.assertIn(rule_id, self.rules)
                domain = self.rules[rule_id].get("domain_force", "")
                self.assertIn("('company_id', '=', False)", domain)
                self.assertIn("('company_id', 'in', company_ids)", domain)

    def test_internal_price_rule_keeps_project_membership_scope(self):
        for model, rule_id in INTERNAL_RULES.items():
            with self.subTest(model=model):
                domain = self.rules[rule_id].get("domain_force", "")
                self.assertIn("('project_id', '=', False)", domain)
                self.assertIn("('create_uid', '=', user.id)", domain)
                self.assertIn("('project_id.user_id', '=', user.id)", domain)
                self.assertIn(
                    "('project_id.message_follower_ids.partner_id', '=', user.partner_id.id)",
                    domain,
                )

    def test_internal_price_rule_keeps_its_permissions(self):
        for model, rule_id in INTERNAL_RULES.items():
            with self.subTest(model=model):
                record = self.rules[rule_id]
                self.assertEqual(record.get("perm_read"), "True")
                self.assertEqual(record.get("perm_write"), "True")
                self.assertEqual(record.get("perm_create"), "True")
                self.assertEqual(record.get("perm_unlink"), "False")

    def test_internal_price_rule_stays_group_scoped(self):
        for model, rule_id in INTERNAL_RULES.items():
            with self.subTest(model=model):
                record = self.rules[rule_id]
                self.assertIn("group_sc_internal_user", record.get("groups", ""))
                self.assertIsNone(record.get("global"))

    def test_super_admin_rule_still_covers_the_price_model(self):
        for model, rule_id in SUPER_ADMIN_RULES.items():
            with self.subTest(model=model):
                self.assertIn(rule_id, self.rules)
                record = self.rules[rule_id]
                self.assertEqual(record.get("domain_force"), "[(1,'=',1)]")
                self.assertIn("group_sc_super_admin", record.get("groups", ""))

    def test_material_price_sibling_rule_is_unchanged(self):
        catalogue = self.rules["rule_sc_material_read_catalog_company"]
        self.assertIn(
            "('company_id', 'in', company_ids)", catalogue.get("domain_force", "")
        )
        material = self.rules["rule_sc_material_user_price"]
        domain = material.get("domain_force", "")
        self.assertIn("('company_id', 'in', company_ids)", domain)
        self.assertIn("('project_id', '=', False)", domain)


class MaterialSiblingDeclarationTests(unittest.TestCase):
    """The proven sibling stays the reference shape for a derived company."""

    def test_material_price_derives_company_from_its_catalogue(self):
        source = (MODEL_ROOT / "material_catalog.py").read_text(encoding="utf-8")
        self.assertIn('related="material_catalog_id.company_id", store=True', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)

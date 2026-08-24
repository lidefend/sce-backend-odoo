#!/usr/bin/env python3

from __future__ import annotations

import unittest

from scripts.verify.scene_audit_disclosure_guard import audit_disclosure_is_governed


def component(attributes: str) -> str:
    return f'''<template>
  <details {attributes}>
    <summary>Audit</summary>
    <div data-audit-content />
  </details>
</template>
<script setup lang="ts"></script>
'''


class SceneAuditDisclosureGuardTests(unittest.TestCase):
    def test_accepts_content_backed_disclosure_collapsed_by_default(self) -> None:
        self.assertTrue(audit_disclosure_is_governed(component(
            'v-if="auditNodes.length || auditEvents.length" data-floorplan-region="audit"',
        )))
        self.assertTrue(audit_disclosure_is_governed(component(
            'data-floorplan-region="audit" v-if="(auditEvents.length) || (auditNodes.length)"',
        )))

    def test_rejects_default_expanded_variants(self) -> None:
        for expanded in ('open', ':open="true"', 'v-bind:open="true"', 'v-bind="{ open: true }"'):
            with self.subTest(expanded=expanded):
                self.assertFalse(audit_disclosure_is_governed(component(
                    f'v-if="auditNodes.length || auditEvents.length" {expanded} data-floorplan-region="audit"',
                )))

    def test_rejects_declared_but_empty_audit_shell(self) -> None:
        self.assertFalse(audit_disclosure_is_governed(component(
            'v-if="hasAudit || auditNodes.length || auditEvents.length" data-floorplan-region="audit"',
        )))

    def test_accepts_declared_professional_empty_state(self) -> None:
        source = component(
            'v-if="declared || events.length || fallbackAvailable" data-floorplan-region="audit"',
        ).replace('<div data-audit-content />', '<div data-audit-readable-fallback /><ScEmptyState />')
        self.assertTrue(audit_disclosure_is_governed(source))

    def test_comments_and_unrelated_strings_cannot_fake_compliance(self) -> None:
        source = '''<template><section /></template>
<!-- <details v-if="auditNodes.length || auditEvents.length" data-floorplan-region="audit"> -->
<script setup lang="ts">
const unrelated = '<details v-if="auditNodes.length || auditEvents.length" data-floorplan-region="audit">';
</script>
'''
        self.assertFalse(audit_disclosure_is_governed(source))

    def test_rejects_missing_or_duplicate_audit_disclosures(self) -> None:
        self.assertFalse(audit_disclosure_is_governed('<template><section /></template>'))
        valid = component('v-if="auditNodes.length || auditEvents.length" data-floorplan-region="audit"')
        self.assertFalse(audit_disclosure_is_governed(valid.replace('</template>', (
            '<details v-if="auditNodes.length || auditEvents.length" data-floorplan-region="audit" />'
            '</template>'
        ))))


if __name__ == '__main__':
    unittest.main()

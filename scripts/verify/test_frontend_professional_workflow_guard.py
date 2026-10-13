import unittest
from pathlib import Path
from scripts.verify.frontend_professional_workflow_guard import validate

ROOT = Path(__file__).resolve().parents[2]

class ProfessionalWorkflowGuardTests(unittest.TestCase):
    def test_current_sources_pass(self): self.assertEqual(validate(), [])
    def test_broken_shared_action_bindings_fail(self):
        cases = (
            ("ContractFormDriverHost.vue", ':direct-actions="directActions"', ':direct-actions="[]"', "TaskFormPattern"),
            ("ContractFormDriverHost.vue", ':overflow-actions="overflowActions"', ':overflow-actions="[]"', "WorkspaceFormPattern"),
            ("ContractFormDriverHost.vue", ':direct-actions="floorplan.directActions"', ':direct-actions="[]"', "task compatibility"),
            ("CanonicalNativeFormSurface.vue", ':direct-actions="directActions"', ':direct-actions="[]"', "native surface"),
            ("CanonicalNativeFormSurface.vue", ':overflow-actions="overflowActions"', ':overflow-actions="[]"', "native surface"),
            ("CanonicalNativeFormSurface.vue", ':effective-primary-key="effectivePrimaryKey"', ':effective-primary-key="null"', "native surface"),
            ("CanonicalNativeFormSurface.vue", '@action-ref="emit(\'action-ref\', $event)"', '@action-ref="undefined"', "native surface"),
            ("CanonicalNativeFormSurface.vue", 'v-if="visibleActions.length && !actionsInHeader"', 'v-if="true"', "header ownership"),
            ("CanonicalNativeFormSurface.vue", "import CanonicalActionBar from './CanonicalActionBar.vue';", "", "import missing"),
        )
        for filename, before, after, reason in cases:
            with self.subTest(filename=filename, binding=before):
                def read_text(path):
                    value = (ROOT / path).read_text(encoding="utf-8")
                    if not path.endswith(filename):
                        return value
                    self.assertIn(before, value)
                    return value.replace(before, after)
                self.assertTrue(any(reason in item for item in validate(read_text)))

    def test_initial_guidance_cannot_return_to_body(self):
        for source in ('<section v-if="warnings.length"><li v-for="row in warnings">{{row}}</li></section>',
                       '<section v-if="workflowEvidenceGateRows.length">{{workflowEvidenceGateRows}}</section>'):
            def read_text(path):
                text = (ROOT / path).read_text(encoding="utf-8")
                return text.replace('<template>', '<template>' + source, 1) if path.endswith('ContractFormActionBlocks.vue') else text
            self.assertTrue(any('permanent body' in error for error in validate(read_text)))

    def test_strict_gap_stop_cannot_be_removed_with_guidance(self):
        def read_text(path):
            text = (ROOT / path).read_text(encoding="utf-8")
            return text.replace('v-if="strictContractMissingSummary && !isIntakeCreateMode"', 'v-if="false"') if path.endswith('ContractFormActionBlocks.vue') else text
        self.assertTrue(any('explicit stop' in error for error in validate(read_text)))

    def test_synthesized_task_blocker_cannot_return(self):
        def read_text(path):
            text = (ROOT / path).read_text(encoding="utf-8")
            return text.replace('<template>', '<template><strong>{{blockedActionMessage}}</strong>', 1) if path.endswith('ObjectTaskPage.vue') else text
        self.assertTrue(any('task blocker' in error for error in validate(read_text)))

    def test_missing_action_marker_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('data-professional-workflow-component="action-bar"', "data-marker-removed")
        self.assertTrue(any("action bar missing" in item for item in validate(read_text)))
    def test_special_case_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n// project.project\n" if path.endswith("professionalWorkflowModel.ts") else value
        self.assertTrue(any("forbidden product special case" in item for item in validate(read_text)))
    def test_missing_dialog_purpose_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('data-dialog-purpose="intent-confirmation"', "data-purpose-removed")
        self.assertTrue(any("dialog purpose" in item for item in validate(read_text)))

if __name__ == "__main__": unittest.main()

import unittest
from pathlib import Path
from scripts.verify.frontend_professional_collaboration_guard import validate

ROOT = Path(__file__).resolve().parents[2]
class ProfessionalCollaborationGuardTests(unittest.TestCase):
    def test_current_sources_pass(self): self.assertEqual(validate(), [])
    def test_missing_timeline_identity_fails(self):
        def read_text(path): return (ROOT / path).read_text(encoding="utf-8").replace('data-professional-collaboration-component="timeline"', 'data-marker-removed')
        self.assertTrue(any("timeline missing" in item for item in validate(read_text)))
    def test_follower_cannot_be_claimed_ready(self):
        def read_text(path): return (ROOT / path).read_text(encoding="utf-8").replace("follower: 'fail_closed'", "follower: 'ready'")
        self.assertTrue(any("follower runtime" in item for item in validate(read_text)))
    def test_raw_composer_textarea_fails(self):
        def read_text(path): return (ROOT / path).read_text(encoding="utf-8").replace("<ScTextarea", "<textarea")
        self.assertTrue(any("raw textarea" in item for item in validate(read_text)))
    def test_raw_attachment_input_fails(self):
        def read_text(path): return (ROOT / path).read_text(encoding="utf-8").replace("<ScFileField", '<input type="file"')
        self.assertTrue(any("file primitive" in item for item in validate(read_text)))
    def test_attachment_download_fail_open_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalCollaborationTimeline.vue"):
                return value.replace("canDownloadCollaborationAttachment(entry)", "entry.attachment?.can_download !== false")
            return value
        self.assertTrue(any("fail-open authority" in item for item in validate(read_text)))
    def test_attachment_open_handler_cannot_bypass_authority(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useNativeAttachmentRuntime.ts"):
                return value.replace(" || att.can_download !== true", "")
            return value
        self.assertTrue(any("independently reject" in item for item in validate(read_text)))
    def test_attachment_upload_handler_cannot_bypass_authority(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useNativeAttachmentRuntime.ts"):
                return value.replace(" || !params.canUpload()", "", 1)
            return value
        self.assertTrue(any("upload handlers" in item for item in validate(read_text)))
    def test_attachment_upload_control_cannot_use_aggregate_authority(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("NativeCollaborationPanel.vue"):
                return value.replace(':enabled="attachmentUploadEnabled"', ':enabled="hasAttachments"')
            return value
        self.assertTrue(any("upload presentation" in item for item in validate(read_text)))
    def test_activity_update_handler_cannot_bypass_authority(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useNativeChatterRuntime.ts"):
                return value.replace(" || !canUpdateCollaborationActivity(entry, action)", "")
            return value
        self.assertTrue(any("activity update handler" in item for item in validate(read_text)))
    def test_activity_update_missing_authority_cannot_fail_open(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalCollaborationModel.ts"):
                return value.replace("entry.activity?.can_complete === true", "entry.activity?.can_complete !== false")
            return value
        self.assertTrue(any("both actions" in item for item in validate(read_text)))
    def test_collaboration_create_handler_cannot_bypass_authority(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useNativeChatterRuntime.ts"):
                return value.replace("if (!canExecuteCollaborationCreateAction(action, activeMode.value)) return;", "")
            return value
        self.assertTrue(any("create handlers" in item for item in validate(read_text)))
    def test_activity_action_cannot_fall_back_to_another_contract_row(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordCollaborationPresentation.ts"):
                return value.replace(")) || null);", ")) || nativeChatterActions.value.find((item) => item.mode === 'activity') || null);", 1)
            return value
        self.assertTrue(any("must not fall back" in item for item in validate(read_text)))
    def test_activity_status_cannot_be_inferred_from_client_clock(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("professionalCollaborationModel.ts"):
                return value.replace("const deadline =", "const now = new Date();\n  const deadline =")
            return value
        self.assertTrue(any("client clock" in item for item in validate(read_text)))
if __name__ == "__main__": unittest.main()

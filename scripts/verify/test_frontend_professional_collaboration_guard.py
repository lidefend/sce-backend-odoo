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
if __name__ == "__main__": unittest.main()

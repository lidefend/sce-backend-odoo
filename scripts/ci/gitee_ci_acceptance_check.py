"""Server-owned check entry, executed only inside the credential-free sandbox."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, '/work')
suite = unittest.defaultTestLoader.loadTestsFromName('scripts.ops.test_gitee_temporary_integration')
result = unittest.TextTestRunner(verbosity=2).run(suite)
count = result.testsRun - len(result.skipped)
Path('/work/.ci-count.json').write_text(json.dumps({'tests': count, 'ok': result.wasSuccessful()}))
raise SystemExit(0 if result.wasSuccessful() and count > 0 else 1)

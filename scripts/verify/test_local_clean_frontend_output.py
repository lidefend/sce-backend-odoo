import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'dev/local_clean_frontend_output_prepare.sh'


class CleanOutputTests(unittest.TestCase):
    def run_case(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=root/'frontend/apps/web/dist-clean'
            target.parent.mkdir(parents=True)
            project='sc-local-dev' if mode=='wrong_profile' else 'sc-local-clean'
            output='frontend/apps/web/dist-dev' if mode=='wrong_output' else 'frontend/apps/web/dist-clean'
            env_file=root/'env'
            env_file.write_text(f"COMPOSE_PROJECT_NAME={project}\nDB_NAME=sc_clean\nODOO_DBFILTER='^sc_clean$'\nFRONTEND_DIST_DIR={output}\n")
            if mode=='symlink':
                other=root/'other';other.mkdir();target.symlink_to(other)
            result=subprocess.run(['bash',str(SCRIPT)],env={**os.environ,'ROOT_DIR':str(root),'ENV_FILE':str(env_file)},capture_output=True,text=True)
            return result, target.is_dir() and not target.is_symlink()

    def test_declared_clean_output_is_created(self):
        result,created=self.run_case('correct')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(created)

    def test_wrong_profile_path_and_symlink_are_rejected(self):
        for mode in ('wrong_profile','wrong_output','symlink'):
            with self.subTest(mode=mode):
                result,created=self.run_case(mode)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(created)

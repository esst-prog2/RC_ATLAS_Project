"""Run one existing workflow test in the verified UI-01 disposable runtime."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

runtime_path = Path('D:/RC_ATLAS_UI01_20261106/docs/ui-01/runtime.py')
spec = importlib.util.spec_from_file_location('ui01_runtime', runtime_path)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
subprocess.run([sys.executable, str(runtime_path), 'verify'], env=runtime.environment_cache,
               capture_output=True, check=True)
os.environ.clear()
os.environ.update(runtime.environment_cache)
os.environ['LOGITRACK_DATA_PATH'] = str(runtime.ROOT / 'hw11-test-default.json')
os.environ['LOGITRACK_SQLITE_PATH'] = str(runtime.ROOT / 'hw11-test-default.sqlite')
os.chdir(runtime.APP)
sys.path.insert(0, str(runtime.APP))
sys.path.insert(0, str(runtime_path.parent))
from runtime_guard import install
install(runtime.ROOT)
name = ('assignment_aware_task_workflow_tests.AssignmentAwareTaskWorkflowTests.'
        'test_capable_but_non_designated_reviewers_are_rejected')
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(name))
print(json.dumps({'test': name, 'run': result.testsRun, 'failures': len(result.failures),
                  'errors': len(result.errors), 'skipped': len(result.skipped),
                  'passed': result.wasSuccessful() and not result.skipped}))
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)

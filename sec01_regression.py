"""Focused SEC-01 evidence runner; no canonical runtime or external providers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=['reproduction', 'postgresql-reproduction', 'postgresql', 'compatibility', 'followup',
                                          'snapshot-before', 'snapshot', 'snapshot-compatibility',
                                          'report-preview-before', 'report-preview', 'report-preview-compatibility'], required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--runtime-parent', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    parent = args.runtime_parent.resolve(strict=True)
    evidence = args.evidence.resolve()
    if evidence.exists():
        raise RuntimeError('Use a new evidence directory; never overwrite prior results.')
    if not evidence.is_relative_to(source / 'sec01-evidence'):
        raise RuntimeError('Evidence must be in this security worktree.')
    worktrees = subprocess.check_output(['git', '-C', str(source), 'worktree', 'list', '--porcelain'], text=True)
    contained_runtime = parent == source / '.sec01-disposable' and not parent.is_symlink()
    for line in worktrees.splitlines():
        if line.startswith('worktree ') and parent.is_relative_to(Path(line[9:]).resolve()):
            if not contained_runtime:
                raise RuntimeError('Use an external disposable root or this worktree dedicated .sec01-disposable root.')
    runtime = Path(tempfile.mkdtemp(prefix='sec01_', dir=parent)).resolve()
    temporary = runtime / 'temp'
    temporary.mkdir()
    if not runtime.is_relative_to(parent) or runtime == parent:
        raise RuntimeError('Runtime containment failed.')
    retained = {k: v for k, v in os.environ.items() if k.upper() in {
        'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATH', 'PATHEXT', 'SYSTEMDRIVE',
        'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'NUMBER_OF_PROCESSORS',
        'PROCESSOR_ARCHITECTURE', 'RCATLAS_PG_TEST_BIN',
    }}
    os.environ.clear()
    os.environ.update(retained)
    os.environ.update(TEMP=str(temporary), TMP=str(temporary), PYTHONDONTWRITEBYTECODE='1',
        RCATLAS_PG_TEST_ROOT=str(runtime), LOGITRACK_STORAGE_BACKEND='json',
        LOGITRACK_DATA_PATH=str(runtime / 'synthetic.json'), LOGITRACK_SQLITE_PATH=str(runtime / 'synthetic.sqlite3'),
        LOGITRACK_RELATIONAL_STORE_PATH=str(runtime / 'projection.sqlite3'),
        LOGITRACK_RUN_SCHEDULER='false', LOGITRACK_EMAIL_ENABLED='false',
        LOGITRACK_ENABLE_RELATIONAL_MIRROR='false', LOGITRACK_ENABLE_REPOSITORY_DOMAINS='false',
        LOGITRACK_ENVIRONMENT='development', LOGITRACK_SESSION_COOKIE_SECURE='false')
    tempfile.tempdir = str(temporary)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    os.chdir(runtime)
    evidence.mkdir(parents=True)
    isolation = {'source': str(source), 'runtime': str(runtime), 'temp': tempfile.gettempdir(),
                 'providers_disabled': True, 'synthetic_only': True, 'canonical_paths': {
                     k: v for k, v in os.environ.items() if k.startswith('LOGITRACK_') and k.endswith('_PATH')}}
    for value in isolation['canonical_paths'].values():
        if not Path(value).resolve().is_relative_to(runtime):
            raise RuntimeError('Unisolated canonical path.')
    (evidence / 'isolation.json').write_text(json.dumps(isolation, indent=2), encoding='utf-8')
    if args.suite.startswith(('snapshot', 'report-preview')):
        golden = source / 'sec01-evidence' / 'rework-before' / 'full-snapshot.json'
        os.environ['SEC01_SNAPSHOT_GOLDEN'] = str(golden)
        os.environ['SEC01_CAPTURE_SNAPSHOT'] = 'true' if args.suite == 'snapshot-before' else 'false'
        if args.suite == 'snapshot-before' and golden.parent != evidence:
            raise RuntimeError('Capture must use the dedicated, new rework-before directory.')
    if args.suite.startswith('report-preview'):
        golden = source / 'sec01-evidence' / 'report-preview-before' / 'full-reports.json'
        os.environ['SEC01_REPORT_GOLDEN'] = str(golden)
        os.environ['SEC01_CAPTURE_REPORT'] = 'true' if args.suite == 'report-preview-before' else 'false'
        if args.suite == 'report-preview-before' and golden.parent != evidence:
            raise RuntimeError('Report capture must use its dedicated, new evidence directory.')
    modules = {
        'reproduction': ['sec01_permission_tests'],
        'postgresql-reproduction': ['sec01_permission_postgresql_tests'],
        'postgresql': ['sec01_permission_postgresql_tests', 'methodology_postgresql_tests', 'analytical_postgresql_tests'],
        'followup': ['sec01_permission_tests', 'repository_tests', 'security_tenant_stabilization_tests'],
        'snapshot-before': ['sec01_snapshot_tests'],
        'snapshot': ['sec01_snapshot_tests'],
        'snapshot-compatibility': ['sec01_snapshot_tests', 'sec01_permission_tests', 'methodology_core_tests',
            'methodology_api_tests', 'analytical_consumer_tests', 'demo_smoke_tests',
            'security_tenant_stabilization_tests', 'session_security_tests'],
        'report-preview-before': ['sec01_report_preview_tests'],
        'report-preview': ['sec01_report_preview_tests', 'sec01_snapshot_tests'],
        'report-preview-compatibility': ['sec01_report_preview_tests', 'sec01_snapshot_tests', 'sec01_permission_tests',
            'methodology_core_tests', 'methodology_api_tests', 'analytical_consumer_tests', 'demo_smoke_tests',
            'security_tenant_stabilization_tests', 'session_security_tests'],
        'compatibility': ['sec01_permission_tests', 'repository_tests', 'logitrack_smoke_tests',
            'demo_smoke_tests', 'security_tenant_stabilization_tests', 'session_security_tests',
            'secure_initialization_tests', 'methodology_core_tests', 'methodology_api_tests',
            'analytical_consumer_tests', 'route_compatibility_tests', 'assignment_aware_task_workflow_tests'],
    }[args.suite]
    source_paths = sorted(set([
        'LogiTrackRC v4.4.py', 'shared/domain_models.py', 'shared/permission_policy.py',
        'repositories/users.py', 'logitrack_platform/relational_store.py',
        'sec01_regression.py', 'sec01_permission_tests.py', 'sec01_permission_postgresql_tests.py',
        'security_tenant_stabilization_tests.py',
        'services/demo_workspace.py', 'services/analytical_authorization.py', 'sec01_snapshot_tests.py',
    ] + [name + '.py' for name in modules]))

    def source_hashes():
        return {name: hashlib.sha256((source / name).read_bytes()).hexdigest() if (source / name).exists() else None
                for name in source_paths}

    tested_hashes = source_hashes()
    (evidence / 'source.json').write_text(json.dumps({
        'head': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
        'sha256': tested_hashes,
    }, indent=2), encoding='utf-8')
    records = []
    class Result(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test); records.append({'test': test.id(), 'status': 'PASS'})
        def addFailure(self, test, err):
            super().addFailure(test, err); records.append({'test': test.id(), 'status': 'FAIL'})
        def addError(self, test, err):
            super().addError(test, err); records.append({'test': test.id(), 'status': 'ERROR'})
        def addSkip(self, test, reason):
            super().addSkip(test, reason); records.append({'test': test.id(), 'status': 'SKIP', 'reason': reason})
        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                records.append({'test': subtest.id(), 'status': 'FAIL' if issubclass(err[0], test.failureException) else 'ERROR'})
    started = time.monotonic()
    class RepositorySuite(unittest.TestSuite):
        def run(self, result, debug=False):
            # These tests exercise repository sync deliberately. Their databases
            # are temporary; enabling the feature never changes runtime paths.
            with patch.dict(os.environ, {'LOGITRACK_ENABLE_REPOSITORY_DOMAINS': 'true'}):
                return super().run(result, debug)

    suite = unittest.TestSuite()
    for name in modules:
        module_suite = unittest.defaultTestLoader.loadTestsFromName(name)
        suite.addTest(RepositorySuite([module_suite]) if name == 'repository_tests' else module_suite)
    with (evidence / 'tests.txt').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Result).run(suite)
    summary = {'suite': args.suite, 'tests': result.testsRun, 'failures': len(result.failures),
               'errors': len(result.errors), 'skips': len(result.skipped), 'seconds': round(time.monotonic() - started, 3),
               'runtime': str(runtime), 'source_unchanged': tested_hashes == source_hashes(), 'records': records}
    (evidence / 'results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}), flush=True)
    return 0 if result.wasSuccessful() and not result.skipped and summary['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Run focused/new/full tests with synthetic paths and explicit backend evidence."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=['core', 'focused', 'all'], required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    parent = Path(os.environ['RCATLAS_PG_TEST_ROOT']).resolve(strict=True)
    runtime = Path(tempfile.mkdtemp(prefix='method_regression_', dir=parent)).resolve()
    assert runtime.is_relative_to(parent) and runtime != parent
    for name in list(os.environ):
        if name.startswith(('LOGITRACK_', 'PG')):
            os.environ.pop(name)
    os.environ.update(LOGITRACK_STORAGE_BACKEND='json', LOGITRACK_DATA_PATH=str(runtime / 'fallback.json'),
                      LOGITRACK_SQLITE_PATH=str(runtime / 'fallback.sqlite3'),
                      LOGITRACK_RELATIONAL_STORE_PATH=str(runtime / 'warehouse.sqlite3'),
                      LOGITRACK_RUN_SCHEDULER='false', LOGITRACK_EMAIL_ENABLED='false', PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode = True
    os.chdir(runtime)
    sys.path.insert(0, str(source))
    records = []

    class EvidenceResult(unittest.TextTestResult):
        def record(self, test, status):
            records.append({'test': test.id(), 'status': status,
                            'mode': 'postgresql' if test.id().startswith(('postgresql_persistence_tests.', 'methodology_postgresql_tests.')) else 'unit_api_source'})

        def addSuccess(self, test):
            super().addSuccess(test); self.record(test, 'PASS')

        def addFailure(self, test, err):
            super().addFailure(test, err); self.record(test, 'FAIL')

        def addError(self, test, err):
            super().addError(test, err); self.record(test, 'ERROR')

        def addSkip(self, test, reason):
            super().addSkip(test, reason); self.record(test, 'SKIP')

    loader = unittest.defaultTestLoader
    if args.suite == 'all':
        suite = loader.discover(str(source), pattern='*_tests.py', top_level_dir=str(source))
    else:
        names = ['methodology_core_tests']
        if args.suite == 'focused':
            names += ['methodology_api_tests', 'methodology_postgresql_tests']
        suite = loader.loadTestsFromNames(names)
    start = time.monotonic()
    with (evidence / 'tests.txt').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=EvidenceResult).run(suite)
    summary = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
               'seconds': round(time.monotonic() - start, 3), 'runtime': str(runtime), 'source': str(source),
               'records': records, 'postgresql_tests': sum(r['mode'] == 'postgresql' for r in records)}
    (evidence / 'results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (evidence / 'isolation.json').write_text(json.dumps({'runtime': str(runtime), 'source': str(source),
        'synthetic_only': True, 'providers_disabled': True, 'canonical_paths': {k: v for k, v in os.environ.items() if k.endswith('_PATH') and k.startswith('LOGITRACK_')}}, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}), flush=True)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == '__main__':
    raise SystemExit(main())

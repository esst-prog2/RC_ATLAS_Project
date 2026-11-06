"""Run focused/full regression with isolated fallback paths and backend accounting."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--suite',choices=['focused','all'],required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    source=Path(__file__).resolve().parent
    evidence=args.evidence.resolve()
    evidence.mkdir(parents=True,exist_ok=True)
    disposable_parent=Path(os.environ['RCATLAS_PG_TEST_ROOT']).resolve(strict=True)
    runtime=Path(tempfile.mkdtemp(prefix='regression_',dir=disposable_parent)).resolve()
    assert runtime.is_relative_to(disposable_parent) and runtime!=disposable_parent
    for name in list(os.environ):
        if name.startswith(('LOGITRACK_','PG')):
            os.environ.pop(name)
    os.environ.update(LOGITRACK_STORAGE_BACKEND='json',LOGITRACK_DATA_PATH=str(runtime/'fallback.json'),
                      LOGITRACK_RUN_SCHEDULER='false',LOGITRACK_EMAIL_ENABLED='false',
                      PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode=True
    os.chdir(runtime)
    sys.path.insert(0,str(source))
    records=[]
    class EvidenceResult(unittest.TextTestResult):
        def record(self,test,status):
            records.append({'test':test.id(),'status':status,
                            'mode':'postgresql' if test.id().startswith('postgresql_persistence_tests.') else 'legacy_or_source'})
        def addSuccess(self,test):
            super().addSuccess(test);self.record(test,'PASS')
        def addError(self,test,err):
            super().addError(test,err);self.record(test,'ERROR')
        def addFailure(self,test,err):
            super().addFailure(test,err);self.record(test,'FAIL')
        def addSkip(self,test,reason):
            super().addSkip(test,reason);self.record(test,'SKIP')
    loader=unittest.defaultTestLoader
    suite=loader.loadTestsFromName('postgresql_persistence_tests') if args.suite=='focused' else loader.discover(
        str(source),pattern='*_tests.py',top_level_dir=str(source))
    start=time.monotonic()
    with (evidence/'tests.txt').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(suite)
    summary={'suite':args.suite,'tests':result.testsRun,'failures':len(result.failures),
             'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.monotonic()-start,3),
             'runtime':str(runtime),'records':records,'source':str(source),
             'postgresql_tests':sum(r['mode']=='postgresql' for r in records),
             'legacy_or_source_tests':sum(r['mode']=='legacy_or_source' for r in records)}
    (evidence/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='records'}),flush=True)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__=='__main__':
    raise SystemExit(main())

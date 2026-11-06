"""Real process, database restart, backup/restore, and optional Chrome acceptance.

Only creates fresh disposable clusters/databases via postgresql_test_support.
"""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from logitrack_platform.postgresql_store import PostgreSQLStore, migrate_schema
from postgresql_test_support import DisposablePostgres, ROOT, free_port
from wave1_session_restart_acceptance import BrowserSession, PASSWORD, seed_fixture, stop_server


def start_server(cluster,env,port):
    log=(cluster.root/f'uvicorn-{port}-{time.time_ns()}.log').open('w',encoding='utf-8')
    command=[sys.executable,'-m','uvicorn','logitrack_rc_v4_4_api:app',
             '--host','127.0.0.1','--port',str(port),'--log-level','warning']
    process=subprocess.Popen(command,cwd=cluster.root,env=env,stdout=log,stderr=log)
    log.close()
    check=BrowserSession(f'http://127.0.0.1:{port}')
    for _ in range(120):
        if process.poll() is not None: raise RuntimeError('Isolated API exited before readiness; inspect runtime log.')
        try:
            check.request('GET','/health')
            return process
        except Exception:
            time.sleep(.25)
    stop_server(process)
    raise RuntimeError('Isolated PostgreSQL API did not become ready.')


def initialize(cluster,database):
    with patch.dict(os.environ,cluster.app_environment(database),clear=True):
        os.environ['LOGITRACK_DATABASE_URL']=cluster.dsn(database,owner=True)
        migrate_schema()
    cluster.grant_application(database)


def run(evidence, browser=False):
    evidence.mkdir(parents=True,exist_ok=True)
    cluster=DisposablePostgres()
    processes=[]
    checks=[]
    def passed(name,**details):
        checks.append({'id':name,'status':'PASS',**details})
        print(name+': PASS',flush=True)
    summary={'backend':'postgresql','synthetic_only':True,'checks':checks,
             'credentials_recorded':False,'runtime_root':str(cluster.root)}
    try:
        cluster.start()
        database=cluster.create_database()
        initialize(cluster,database)
        env=cluster.app_environment(database) | {
            'LOGITRACK_ENVIRONMENT':'development','LOGITRACK_SESSION_COOKIE_SECURE':'false'}
        with patch.dict(os.environ,env,clear=True):
            from logitrack_rc_v4_4_api import module
            seed_fixture(module)
            store=PostgreSQLStore()
            summary['versions']=store.status()
            port1,port2=free_port(),free_port()
            one=start_server(cluster,env,port1)
            two=start_server(cluster,env,port2)
            processes.extend([one,two])
            a=BrowserSession(f'http://127.0.0.1:{port1}')
            a.request('POST','/v1/auth/login',{'username':'restart.admin.a','password':PASSWORD})
            copied_cookie=a.cookie('rcatlas_session_dev')
            a2=BrowserSession(f'http://127.0.0.1:{port2}')
            for cookie in a.jar: a2.jar.set_cookie(copy.copy(cookie))
            version=a.request('GET','/v1/admin/projects')['workspace_version']
            payload={'project_name':'PG Process Project','programme':'Synthetic','donor':'Synthetic',
                     'implementing_partner':'Synthetic','sector':'Education','description':'Disposable PostgreSQL',
                     'country':'Testland','start_date':'2026-01-01','end_date':'2026-12-31'}
            headers={'X-Idempotency-Key':'process-duplicate','X-Workspace-Version':str(version)}
            def create(session): return session.request('POST','/v1/admin/projects',payload,headers=headers)
            with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(create,[a,a2]))
            assert responses[0]==responses[1]
            project_id=responses[0]['project']['id']
            assert len(store.load()['projects'])==1 and len(store.load()['idempotency_records'])==1
            passed('TWO_PROCESS_IDEMPOTENCY',pids=[one.pid,two.pid],resources=1,receipts=1)
            a.request('POST','/v1/admin/projects',dict(payload,project_name='Stale'),
                      headers={'X-Idempotency-Key':'stale','X-Workspace-Version':str(version)},expected=409)
            passed('TWO_PROCESS_STALE_VERSION')
            a.request('POST','/v1/tidy_datasets/import',{'name':'PG Process Dataset','rows':[{'period':'2026-01','value':42}]})
            before=store.load()
            stop_server(one)
            replacement=start_server(cluster,env,port1)
            processes.append(replacement)
            assert replacement.pid!=one.pid
            assert a.request('GET','/v1/auth/me')['user']['username']=='restart.admin.a'
            assert a.request('POST','/v1/admin/projects',payload,headers=headers)==responses[0]
            assert store.load()==before
            passed('API_RESTART_SESSION_PROJECT_DATASET_VERSION_RECEIPT',before_pid=one.pid,
                   after_pid=replacement.pid,workspace_version=before['workspace_version'])
            b=BrowserSession(f'http://127.0.0.1:{port1}')
            b.request('POST','/v1/auth/login',{'username':'restart.admin.b','password':PASSWORD})
            assert not b.request('GET','/v1/admin/projects')['items']
            passed('TENANT_ISOLATION_AFTER_PROCESS_RESTART')
            before=store.load()
            cluster.stop()
            a.request('GET','/v1/auth/me',expected=503)
            cluster.start()
            assert store.load()==before
            a.request('GET','/v1/auth/me')
            passed('POSTGRESQL_SERVER_OUTAGE_AND_RESTART',workspace_version=before['workspace_version'])
            a.request('POST','/v1/auth/logout')
            stop_server(replacement)
            third=start_server(cluster,env,port1)
            processes.append(third)
            copied=BrowserSession(f'http://127.0.0.1:{port1}')
            copied.request('GET','/v1/auth/me',headers={'Cookie':f'rcatlas_session_dev={copied_cookie}'},expected=401)
            b.request('GET','/v1/auth/me')
            passed('REVOCATION_AFTER_SECOND_PROCESS_RESTART',revoked_status=401,other_session_status=200)
            # Freeze all application writers before the synthetic backup rehearsal.
            for process in processes: stop_server(process)
            before=store.load()
            dump=cluster.root/'synthetic-recovery.dump'
            cluster._run('pg_dump.exe','-h','127.0.0.1','-p',cluster.port,'-U','rcatlas_owner',
                         '-d',database,'-Fc','-f',dump)
            restored=cluster.create_database()
            cluster._run('pg_restore.exe','-h','127.0.0.1','-p',cluster.port,'-U','rcatlas_owner',
                         '-d',restored,'--exit-on-error',dump)
            cluster.grant_application(restored)
            with patch.dict(os.environ,{'LOGITRACK_DATABASE_URL':cluster.dsn(restored)}):
                assert PostgreSQLStore().load()==before
                assert PostgreSQLStore().status()['postgis_version']=='3.6.2'
            passed('PG_DUMP_RESTORE_TO_NEW_DATABASE',sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),
                   full_payload_equal=True)
        if browser:
            browser_db=cluster.create_database()
            initialize(cluster,browser_db)
            browser_env=cluster.app_environment(browser_db) | {
                'LOGITRACK_ENVIRONMENT':'development','LOGITRACK_SESSION_COOKIE_SECURE':'false',
                'LOGITRACK_SETUP_ENABLED':'true','LOGITRACK_SETUP_TOKEN':'synthetic-browser-setup-token',
            }
            port=free_port()
            server=start_server(cluster,browser_env,port)
            processes.append(server)
            node_env=browser_env | {
                'PLAYWRIGHT_CORE_PATH':str(Path(os.environ['RCATLAS_PG_TEST_ROOT'])/'browser-tools/node_modules/playwright-core'),
                'RCATLAS_BASE_URL':f'http://127.0.0.1:{port}',
                'RCATLAS_CHROME_PATH':os.environ.get('RCATLAS_CHROME_PATH','C:/Program Files/Google/Chrome/Application/chrome.exe'),
                'RCATLAS_EVIDENCE_DIR':str(evidence/'browser'),
            }
            result=subprocess.run(['node',str(ROOT/'postgresql_browser_acceptance.js')],env=node_env,
                                  cwd=cluster.root,capture_output=True,text=True,timeout=240)
            (evidence/'browser-run.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
            if result.returncode: raise RuntimeError('Real Chrome acceptance failed; inspect browser evidence.')
            with patch.dict(os.environ,browser_env,clear=True):
                state=PostgreSQLStore().load()
                assert len(state['projects'])==1 and state['sessions']
            passed('REAL_CHROME_POSTGRESQL_WORKFLOWS',canonical_projects=len(state['projects']))
        summary['status']='PASS'
    except Exception as exc:
        summary['status']='FAIL'
        summary['failure_type']=type(exc).__name__
        raise
    finally:
        for process in processes: stop_server(process)
        cluster.stop()
        summary['owned_processes_stopped']=True
        (evidence/'runtime-results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        (evidence/'runtime-isolation.json').write_text((cluster.root/'isolation.json').read_text(),encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--browser',action='store_true')
    args=parser.parse_args()
    print(json.dumps(run(args.evidence.resolve(),args.browser),indent=2))

"""Actual Uvicorn restart + PostgreSQL restart/restore + installed Chrome acceptance."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlencode
from unittest.mock import patch

from logitrack_platform.postgresql_store import PostgreSQLStore
from postgresql_test_support import DisposablePostgres, ROOT, free_port
from postgresql_runtime_acceptance import initialize, start_server
from wave1_session_restart_acceptance import BrowserSession, stop_server
from methodology_fixtures import AS_OF, PASSWORD, definition_payload, seed

PREFIX = '/v1/projects/project_method/indicators/indicator_method'


def run(evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    cluster = DisposablePostgres()
    processes, checks = [], []
    summary = {'status': 'RUNNING', 'runtime_root': str(cluster.root), 'synthetic_only': True, 'checks': checks}

    def passed(name, **details):
        checks.append({'id': name, 'status': 'PASS', **details})
        print(name + ': PASS', flush=True)

    try:
        cluster.start()
        database = cluster.create_database()
        initialize(cluster, database)
        env = cluster.app_environment(database) | {'LOGITRACK_ENVIRONMENT': 'development', 'LOGITRACK_SESSION_COOKIE_SECURE': 'false'}
        with patch.dict(os.environ, env, clear=True):
            from logitrack_rc_v4_4_api import module
            data = seed(module)
            for user in data.users:
                user.username += '@example.test'
                user.email = user.username
            data.users.append(module.build_user_account_from_payload({
                'id': 'user_method_meal', 'organization_id': 'org_method_a',
                'username': 'method.meal@example.test', 'email': 'method.meal@example.test',
                'full_name': 'Synthetic Methodology MEAL Officer', 'role': 'meal_officer',
                'status': 'active', 'is_active': True, 'password': PASSWORD,
            }))
            # A second unconfigured indicator makes the unavailable state reachable.
            project = data.projects[0]
            project.indicators.append(module.Indicator(id='indicator_unconfigured', name='Unconfigured synthetic indicator',
                unit='people', frequency='monthly', direction='up', level='outcome', target=None, baseline=None,
                organization_id=project.organization_id, project_id=project.id))
            # Existing Studio project loading requires a template, even when
            # this acceptance workflow only inspects the methodology panel.
            data.dashboard_templates = module.build_builtin_dashboard_templates(data.tidy_datasets[0], {})
            for template in data.dashboard_templates:
                template.organization_id = project.organization_id
            module.save_data_to_path(data)
            port = free_port()
            server = start_server(cluster, env, port)
            processes.append(server)
            base = f'http://127.0.0.1:{port}'
            a = BrowserSession(base)
            a.request('POST', '/v1/auth/login', {'username': 'method.a.organization_admin@example.test', 'password': PASSWORD})
            for payload in (definition_payload(quality_rules={'required_fields': ['actual', 'period'], 'conformance': {'actual': {'type': 'number', 'min': 0}}}),
                            definition_payload(methodology_id='schedule-attainment', profile='TIME_PHASED', planned_targets={'2026-09-30': 60})):
                version = a.request('GET', PREFIX + '/methodology')['workspace_version']
                a.request('POST', PREFIX + '/methodology', {'definition': payload, 'expected_workspace_version': version})
            params = {'methodology_id': 'change-achievement', 'version': '1.0.0', 'start': '2026-09-01', 'end': '2026-09-30', 'as_of': AS_OF, 'locale': 'EN'}
            first = a.request('GET', PREFIX + '/calculation?' + urlencode(params))
            assert first['result']['display_value'] == '50.00'
            saved = a.request('POST', PREFIX + '/calculation-instances', dict(params,
                expected_workspace_version=a.request('GET', PREFIX + '/methodology')['workspace_version']))
            history_url = PREFIX + '/calculation-instances/' + saved['result']['calculation_id']
            before = PostgreSQLStore().load()
            stop_server(server)
            replacement = start_server(cluster, env, port)
            processes.append(replacement)
            assert replacement.pid != server.pid
            assert a.request('GET', PREFIX + '/calculation?' + urlencode(params)) == first
            assert a.request('GET', history_url)['result'] == saved['result']
            assert PostgreSQLStore().load() == before
            passed('API_PROCESS_RESTART_EXACT_DEFINITION_INSTANCE_SESSION', previous_pid=server.pid, replacement_pid=replacement.pid)
            cluster.stop()
            a.request('GET', history_url, expected=503)
            cluster.start()
            assert a.request('GET', history_url)['result'] == saved['result']
            assert PostgreSQLStore().load() == before
            passed('POSTGRESQL_RESTART_EXACT_INSTANCE_RECOVERY')
            b = BrowserSession(base)
            b.request('POST', '/v1/auth/login', {'username': 'method.b.organization_admin@example.test', 'password': PASSWORD})
            b.request('GET', history_url, expected=404)
            b.request('GET', PREFIX + '/methodology', expected=404)
            passed('TENANT_BOUNDARY_AFTER_PROCESS_AND_DATABASE_RESTART')
            browser_env = env | {'PLAYWRIGHT_CORE_PATH': os.environ['PLAYWRIGHT_CORE_PATH'],
                'RCATLAS_BASE_URL': base, 'RCATLAS_CHROME_PATH': os.environ['RCATLAS_CHROME_PATH'],
                'RCATLAS_EVIDENCE_DIR': str(evidence / 'browser')}
            result = subprocess.run(['node', str(ROOT / 'methodology_browser_acceptance.js')], env=browser_env,
                                    cwd=cluster.root, capture_output=True, text=True, timeout=240)
            (evidence / 'browser-run.txt').write_text(result.stdout + '\n' + result.stderr, encoding='utf-8')
            if result.returncode:
                raise RuntimeError('Chrome methodology acceptance failed; see retained evidence.')
            passed('REAL_CHROME_WORKFLOW', detail='See browser-results.json for separately counted checks.')
            for process in processes:
                stop_server(process)
            before = PostgreSQLStore().load()
            dump = cluster.root / 'synthetic-methodology.dump'
            cluster._run('pg_dump.exe', '-h', '127.0.0.1', '-p', cluster.port, '-U', 'rcatlas_owner', '-d', database, '-Fc', '-f', dump)
            restored = cluster.create_database()
            cluster._run('pg_restore.exe', '-h', '127.0.0.1', '-p', cluster.port, '-U', 'rcatlas_owner', '-d', restored, '--exit-on-error', dump)
            cluster.grant_application(restored)
            with patch.dict(os.environ, {'LOGITRACK_DATABASE_URL': cluster.dsn(restored)}):
                assert PostgreSQLStore().load() == before
            passed('PG_DUMP_RESTORE_FULL_PAYLOAD_AND_METHOD_HISTORY')
            summary['versions'] = PostgreSQLStore().status()
        summary['status'] = 'PASS'
    except Exception as exc:
        summary['status'] = 'FAIL'
        summary['failure_type'] = type(exc).__name__
        raise
    finally:
        for process in processes:
            stop_server(process)
        cluster.stop()
        summary['owned_processes_stopped'] = True
        (evidence / 'runtime-results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        if (cluster.root / 'isolation.json').exists():
            (evidence / 'runtime-isolation.json').write_text((cluster.root / 'isolation.json').read_text(), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.evidence.resolve()), indent=2))

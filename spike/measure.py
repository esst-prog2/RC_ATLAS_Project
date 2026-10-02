import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.demo_seed import build_demo_seed_bundle

BASE = 'http://127.0.0.1:8000'
PROJECT = 'proj_resilience'
RESULTS = []


def request(path, method='GET', body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-Auth-Token'] = token
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {'detail': raw}
        return exc.code, payload


DEMO_CREDENTIALS = {credential.username: credential.password for credential in build_demo_seed_bundle(lambda password: ('', '')).credentials}


def login(username):
    status, payload = request('/v1/auth/login', 'POST', {'username': username, 'password': DEMO_CREDENTIALS[username]})
    token = payload.get('token', '') if status == 200 else ''
    return status, token


def find_task(value, task_id):
    if isinstance(value, dict):
        if value.get('task_id') == task_id:
            return value
        for child in value.values():
            found = find_task(child, task_id)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_task(child, task_id)
            if found:
                return found
    return None


def verify(token, task_id, expected):
    status, payload = request(f'/v1/demo/projects/{PROJECT}/workplan', token=token)
    task = find_task(payload, task_id) if status == 200 else None
    if not task:
        return False, f'workplan HTTP {status}; task absent'
    for key, value in expected.items():
        if task.get(key) != value:
            return False, f'{key} expected {value!r}, got {task.get(key)!r}'
    return True, 'persisted verified'


def operation(number, actor, action, token, path, body, task_id, expected):
    status, payload = request(path, 'POST', body, token)
    if status < 200 or status >= 300:
        RESULTS.append({'operation': number, 'actor': actor, 'action': action, 'http_status': status, 'success': False, 'persistence': 'not verified', 'detail': payload.get('detail', 'request failed')})
        return False
    persisted, detail = verify(token, task_id, expected)
    RESULTS.append({'operation': number, 'actor': actor, 'action': action, 'http_status': status, 'success': persisted, 'persistence': detail})
    return persisted


try:
    teresa_login, teresa = login('teresa.mbanze')
    if teresa_login != 200:
        raise RuntimeError(f'Teresa login failed with HTTP {teresa_login}')
    if not operation(1, 'Teresa', 'create Task 1 for Aline', teresa, '/v1/demo/tasks', {'id': 'task_hw4_spike_1', 'project_id': PROJECT, 'title': 'HW4 Spike Task 1', 'assignee_username': 'aline.duarte', 'due_date': '2026-12-31'}, 'task_hw4_spike_1', {'status': 'not_started', 'assignee_username': 'aline.duarte'}):
        raise RuntimeError('Stopped after operation 1')

    aline_login, aline = login('aline.duarte')
    if aline_login != 200:
        raise RuntimeError(f'Aline login failed with HTTP {aline_login}')
    if not operation(2, 'Aline', 'update Task 1', aline, '/v1/demo/tasks/task_hw4_spike_1/update', {'status': 'in_progress', 'progress_pct': 25, 'evidence_note': 'HW4 evidence 1', 'comment': 'HW4 progress update 1'}, 'task_hw4_spike_1', {'status': 'in_progress'}):
        raise RuntimeError('Stopped after operation 2')
    if not operation(3, 'Aline', 'submit Task 1', aline, '/v1/demo/tasks/task_hw4_spike_1/update', {'submit_for_validation': True, 'progress_pct': 90, 'comment': 'HW4 submit 1'}, 'task_hw4_spike_1', {'status': 'pending_validation'}):
        raise RuntimeError('Stopped after operation 3')

    raimundo_login, raimundo = login('raimundo.cumba')
    if raimundo_login != 200:
        raise RuntimeError(f'Raimundo login failed with HTTP {raimundo_login}')
    if not operation(4, 'Raimundo', 'validate Task 1', raimundo, '/v1/demo/tasks/task_hw4_spike_1/validate', {'decision': 'validated', 'comment': 'HW4 validation 1'}, 'task_hw4_spike_1', {'status': 'pending_validation'}):
        raise RuntimeError('Stopped after operation 4')

    teresa_login, teresa = login('teresa.mbanze')
    if teresa_login != 200:
        raise RuntimeError(f'Teresa login failed with HTTP {teresa_login}')
    if not operation(5, 'Teresa', 'approve Task 1', teresa, '/v1/demo/tasks/task_hw4_spike_1/validate', {'decision': 'approved', 'comment': 'HW4 approval 1'}, 'task_hw4_spike_1', {'status': 'completed'}):
        raise RuntimeError('Stopped after operation 5')
    if not operation(6, 'Teresa', 'create Task 2 for Aline', teresa, '/v1/demo/tasks', {'id': 'task_hw4_spike_2', 'project_id': PROJECT, 'title': 'HW4 Spike Task 2', 'assignee_username': 'aline.duarte', 'due_date': '2026-12-31'}, 'task_hw4_spike_2', {'status': 'not_started', 'assignee_username': 'aline.duarte'}):
        raise RuntimeError('Stopped after operation 6')

    aline_login, aline = login('aline.duarte')
    if aline_login != 200:
        raise RuntimeError(f'Aline login failed with HTTP {aline_login}')
    if not operation(7, 'Aline', 'update Task 2', aline, '/v1/demo/tasks/task_hw4_spike_2/update', {'status': 'in_progress', 'progress_pct': 25, 'evidence_note': 'HW4 evidence 2', 'comment': 'HW4 progress update 2'}, 'task_hw4_spike_2', {'status': 'in_progress'}):
        raise RuntimeError('Stopped after operation 7')
    if not operation(8, 'Aline', 'submit Task 2', aline, '/v1/demo/tasks/task_hw4_spike_2/update', {'submit_for_validation': True, 'progress_pct': 90, 'comment': 'HW4 submit 2'}, 'task_hw4_spike_2', {'status': 'pending_validation'}):
        raise RuntimeError('Stopped after operation 8')

    checkpoint = {'checkpoint': 'logout/login', 'logout': 'client token discarded', 'login_actor': 'Raimundo'}
    aline = None
    raimundo_login, raimundo = login('raimundo.cumba')
    checkpoint['login_http_status'] = raimundo_login
    if raimundo_login == 200:
        me_status, _ = request('/v1/auth/me', token=raimundo)
        checkpoint['authenticated_request_http_status'] = me_status
    RESULTS.append(checkpoint)
    if raimundo_login != 200 or checkpoint.get('authenticated_request_http_status') != 200:
        raise RuntimeError('Stopped at non-counted login checkpoint')

    if not operation(9, 'Raimundo', 'validate Task 2', raimundo, '/v1/demo/tasks/task_hw4_spike_2/validate', {'decision': 'validated', 'comment': 'HW4 validation 2'}, 'task_hw4_spike_2', {'status': 'pending_validation'}):
        raise RuntimeError('Stopped after operation 9')
    teresa_login, teresa = login('teresa.mbanze')
    if teresa_login != 200:
        raise RuntimeError(f'Teresa login failed with HTTP {teresa_login}')
    if not operation(10, 'Teresa', 'approve Task 2', teresa, '/v1/demo/tasks/task_hw4_spike_2/validate', {'decision': 'approved', 'comment': 'HW4 approval 2'}, 'task_hw4_spike_2', {'status': 'completed'}):
        raise RuntimeError('Stopped after operation 10')
except Exception as exc:
    RESULTS.append({'measurement_stop': str(exc)})
finally:
    with open('measurement_results.json', 'w', encoding='utf-8') as handle:
        json.dump(RESULTS, handle, indent=2)
    print(json.dumps(RESULTS, indent=2))




counted = [item for item in RESULTS if 'operation' in item]
successful = sum(1 for item in counted if item.get('success'))
failed = next((item for item in counted if not item.get('success')), None)
print(f'Successful counted operations: {successful}/10')
print(f"First failing operation: {failed['operation'] if failed else 'none'}")

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path('/Users/gorin/.gorin-skills/openclaw/log-watchdog/scripts/log_watchdog.py')


def load_module():
    spec = importlib.util.spec_from_file_location('log_watchdog_under_test', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class LogWatchdogFailoverTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.log_dir = self.root / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.module.LOG_SOURCE = self.log_dir / 'gateway.err.log'
        self.module.POS_FILE = self.log_dir / 'log-watchdog-pos'
        self.module.STATE_FILE = self.log_dir / 'log-watchdog-state.json'
        self.module.LOCK_FILE = self.root / 'log-watchdog.lock'
        self.module.AGENTS_ROOT = self.root / 'agents'
        self.notifications = []
        self.module.notify = self.notifications.append

    def tearDown(self):
        self.tmp.cleanup()

    def write_log(self, lines):
        self.module.LOG_SOURCE.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def write_session_entry(self, agent_id, session_key, ended_at=None):
        sessions_dir = self.module.AGENTS_ROOT / agent_id / 'sessions'
        sessions_dir.mkdir(parents=True, exist_ok=True)
        payload = {session_key: {}}
        if ended_at is not None:
            payload[session_key]['endedAt'] = ended_at
        (sessions_dir / 'sessions.json').write_text(json.dumps(payload), encoding='utf-8')

    def test_subagent_identity_prefers_session_key_line_over_bare_lane(self):
        lines = [
            '2026-04-12T18:08:03.079+08:00 [diagnostic] lane task error: lane=subagent durationMs=735152 error="FailoverError: LLM request timed out."',
            '2026-04-12T18:08:03.079+08:00 [diagnostic] lane task error: lane=session:agent:edu-assessment:subagent:5a53abac-492d-4351-b32f-a69e58a1a717 durationMs=735152 error="FailoverError: LLM request timed out."',
        ]
        context = self.module.resolve_failover_context(lines, 0)
        self.assertEqual(context['session_key'], 'agent:edu-assessment:subagent:5a53abac-492d-4351-b32f-a69e58a1a717')
        self.assertEqual(context['identity'].agent, 'edu-assessment')
        self.assertEqual(context['identity'].lane, 'subagent')
        self.assertEqual(context['sample_line'], lines[1])

    def test_ended_subagent_auto_recovers_pending_failover_without_second_alert(self):
        session_key = 'agent:edu-assessment:subagent:5a53abac-492d-4351-b32f-a69e58a1a717'
        self.write_session_entry('edu-assessment', session_key)
        self.write_log([
            '2026-04-12T18:08:03.079+08:00 [diagnostic] lane task error: lane=subagent durationMs=735152 error="FailoverError: LLM request timed out."',
            f'2026-04-12T18:08:03.079+08:00 [diagnostic] lane task error: lane=session:{session_key} durationMs=735152 error="FailoverError: LLM request timed out."',
        ])

        rc = self.module._run()
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.notifications), 1)
        self.assertIn('对象: edu-assessment (subagent:5a53abac-492d-4351-b32f-a69e58a1a717)', self.notifications[0])
        state = json.loads(self.module.STATE_FILE.read_text(encoding='utf-8'))
        self.assertIn(session_key, state['pending_failovers'])

        self.write_session_entry('edu-assessment', session_key, ended_at=1775988653350)
        rc = self.module._run()
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.notifications), 1)
        state = json.loads(self.module.STATE_FILE.read_text(encoding='utf-8'))
        self.assertNotIn(session_key, state.get('pending_failovers', {}))

    def test_ended_subagent_followup_lines_after_cooldown_do_not_realert(self):
        session_key = 'agent:edu-assessment:subagent:5a53abac-492d-4351-b32f-a69e58a1a717'
        first_wave = [
            '2026-04-12T18:08:03.079+08:00 [diagnostic] lane task error: lane=subagent durationMs=735152 error="FailoverError: LLM request timed out."',
            f'2026-04-12T18:08:03.079+08:00 [diagnostic] lane task error: lane=session:{session_key} durationMs=735152 error="FailoverError: LLM request timed out."',
        ]
        second_wave = [
            '2026-04-12T19:08:03.079+08:00 [diagnostic] lane task error: lane=subagent durationMs=815152 error="FailoverError: LLM request timed out."',
            f'2026-04-12T19:08:03.079+08:00 [diagnostic] lane task error: lane=session:{session_key} durationMs=815152 error="FailoverError: LLM request timed out."',
        ]

        self.write_session_entry('edu-assessment', session_key)
        self.write_log(first_wave)

        rc = self.module._run()
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.notifications), 1)
        state = json.loads(self.module.STATE_FILE.read_text(encoding='utf-8'))
        self.assertIn(session_key, state['pending_failovers'])

        self.write_session_entry('edu-assessment', session_key, ended_at=1775988653350)
        state['cooldowns']['failover'] = 0
        self.module.STATE_FILE.write_text(json.dumps(state), encoding='utf-8')
        self.write_log(first_wave + second_wave)

        rc = self.module._run()
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.notifications), 1)
        state = json.loads(self.module.STATE_FILE.read_text(encoding='utf-8'))
        self.assertNotIn(session_key, state.get('pending_failovers', {}))

    def test_non_subagent_pending_failover_is_not_auto_recovered(self):
        session_key = 'agent:dev-tl:telegram:group:-1003869255084'
        state = {
            'cooldowns': {},
            'reported_hashes': [],
            'pending_failovers': {
                session_key: {
                    'lane': 'telegram',
                    'agent': 'dev-tl',
                    'subject': 'group:-1003869255084',
                    'firstAlertAt': 1,
                }
            },
        }
        self.module.reconcile_pending_failovers(state, {})
        self.assertIn(session_key, state['pending_failovers'])


if __name__ == '__main__':
    unittest.main()

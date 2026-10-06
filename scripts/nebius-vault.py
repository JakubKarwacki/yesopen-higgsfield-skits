#!/usr/bin/env python3
"""Nebius service-account CLI; private key stays in vault and process memory."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

BINARY = Path.home() / '.local/lib/nebius/nebius'
VAULT = Path.home() / '.agents/skills/agent-passwords/scripts/vault.py'
SETTINGS = Path(os.environ.get('YESOPEN_NEBIUS_CONFIG',
    str(Path.home() / '.config/yesopen-gpu/nebius.json')))


def main():
    args = sys.argv[1:]
    if not args or '--help' in args or '-h' in args or args[0] in {'version', 'completion'}:
        os.execv(str(BINARY), [str(BINARY), *args])
    forbidden = {'--debug', '--insecure', '--endpoint', '--config', '-c', '--profile', '-p'}
    if any(a.split('=', 1)[0] in forbidden for a in args):
        sys.exit('Use the configured secure farm profile; configuration overrides and debug are disabled.')
    if args[0] == 'profile' and (len(args) < 2 or args[1] not in {'list', 'active', 'current'}):
        sys.exit('Service account profile is managed by the vault wrapper.')
    if 'get-access-token' in args:
        sys.exit('Token output is disabled. Credentials stay in the agent vault.')
    if 'compute' in args and any(x in args for x in {'disk', 'filesystem', 'disk-snapshot'}) and 'delete' in args:
        sys.exit('Project policy requires preserving disks and volumes.')
    try:
        settings = json.loads(SETTINGS.read_text())
        entry = settings['vault_entry']
        project = settings['project_id']
        sa = settings['service_account_id']
        key = settings['public_key_id']
        if not all(isinstance(v, str) and v.strip() for v in (entry, project, sa, key)):
            raise ValueError('Missing settings')
    except (OSError, ValueError, KeyError, TypeError):
        sys.exit('Configure your own service account in ~/.config/yesopen-gpu/nebius.json (or YESOPEN_NEBIUS_CONFIG).')
    profile = 'yesopen-farm'
    r = subprocess.run(['/usr/bin/python3', str(VAULT), '_credential', entry], capture_output=True, text=True)
    if r.returncode:
        sys.exit('Cannot read Nebius service-account key from agent vault; details withheld.')
    try:
        credential = json.loads(r.stdout)
        if credential['username'] != sa:
            raise ValueError('account mismatch')
        private_key = base64.b64decode(credential['password']).decode()
        config = {'default': profile, 'profiles': {profile: {
            'endpoint': 'api.nebius.cloud', 'auth-type': 'service account',
            'service-account-id': sa, 'public-key-id': key,
            'private-key': private_key, 'parent-id': project}}}
    except Exception:
        sys.exit('Invalid stored Nebius service-account key; details withheld.')
    reader, writer = os.pipe()
    try:
        payload = json.dumps(config).encode()
        def feed():
            try:
                with os.fdopen(writer, "wb") as stream:
                    stream.write(payload)
            except BrokenPipeError:
                pass
        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
        env = os.environ.copy()
        for name in ('NEBIUS_IAM_TOKEN', 'NEBIUS_PROFILE', 'NEBIUS_ENDPOINT'):
            env.pop(name, None)
        result = subprocess.run([str(BINARY), '--config', f'/dev/fd/{reader}', '--no-browser', *args],
                                pass_fds=(reader,), env=env)
        feeder.join(timeout=2)
        writer = None
        return result.returncode
    finally:
        os.close(reader)
        if writer is not None:
            os.close(writer)

if __name__ == '__main__':
    sys.exit(main())

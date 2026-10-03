#!/usr/bin/env python3
"""Run Verda CLI with project credentials loaded from the encrypted agent vault."""
import json, os, subprocess, sys
from pathlib import Path
args=sys.argv[1:]
allowed={('vm','list'),('vm','describe'),('vm','start'),('vm','shutdown'),('vm','delete'),('volume','list'),('volume','describe')}
if tuple(args[:2]) not in allowed:
    sys.exit('Use vm list/describe/start/shutdown/delete or volume list/describe.')
for arg in args:
    if arg.split('=',1)[0] in {'--debug','--with-volumes','--base-url','--config','--all'}:
        sys.exit('Blocked option: '+arg.split('=',1)[0])
helper=Path.home()/'.agents/skills/agent-passwords/scripts/vault.py'
r=subprocess.run(['/usr/bin/python3',str(helper),'_credential',os.environ.get('VERDA_VAULT_ENTRY','Verda API - YesOpen Video')],capture_output=True,text=True)
if r.returncode: sys.exit('Vault access failed; secret details withheld.')
try: c=json.loads(r.stdout)
except ValueError: sys.exit('Invalid vault response; details withheld.')
env=os.environ.copy()
env.update(VERDA_CLIENT_ID=c['username'],VERDA_CLIENT_SECRET=c['password'],VERDA_DEBUG='false')
os.execvpe('verda',['verda',*sys.argv[1:]],env)

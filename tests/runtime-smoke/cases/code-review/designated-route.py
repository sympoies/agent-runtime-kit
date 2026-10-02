"""Exercise the copyable designated-only route with deterministic tool stubs."""
import os
from pathlib import Path
import re
import subprocess
import sys

root, scratch = map(Path, sys.argv[1:])
scratch.mkdir(parents=True, exist_ok=True)
text = (root / 'core/skills/pr/deliver-pr/references/DESIGNATED_REVIEW_HANDOFF.md').read_text()
block = next(b for b in re.findall(r'```bash\n(.*?)\n```', text, re.S)
             if b.startswith('# Designated-review route only.'))
commands = scratch / 'commands'
bin_dir = scratch / 'bin'
bin_dir.mkdir(exist_ok=True)
stub = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
with open(os.environ['ROUTE_COMMANDS'], 'a') as f: f.write(name+' '+ ' '.join(args)+'\\n')
scenario=os.environ['ROUTE_SCENARIO']
if name=='git': print('b'*40); sys.exit(0)
if name=='agent-session': sys.exit(1 if scenario=='mailbox-failure' else 0)
if '--help' in args: sys.exit(2 if scenario=='old-cli' else 0)
if 'view' in args: print(json.dumps({'ok': True,'data':{'head_sha':'a'*40}})); sys.exit(0)
if 'inspect' in args:
    generation = 2 if scenario == 'recovered' else 1
    handoff = None if scenario == 'initial' else {'reviewer_digest':'configured','assignment_generation':generation}
    status = 'unassigned' if handoff is None else ('surrendered' if scenario=='surrendered' else ('returned-to-coordinator' if scenario=='returned' else 'awaiting-designated-review'))
    if scenario=='conflict' and '--expected-head' in args: sys.exit(65)
    print(json.dumps({'ok':True,'data':{'handoff':handoff,'status':status,'base_sha':'c'*40,
        'handoff_digest':None if handoff is None else 'sha256:'+str(generation)*64,'state_tip_digest':'sha256:'+'f'*64}})); sys.exit(0)
if 'assign' in args:
    required={'--reviewer-session':'reviewer-session@review-machine','--review-author':'review-app[bot]',
              '--base-sha':'c'*40,'--expected-head':'a'*40,'--expected-state':'sha256:'+'f'*64}
    if any(k not in args or args[args.index(k)+1]!=v for k,v in required.items()): sys.exit(65)
    print(json.dumps({'ok':True,'data':{'status':'awaiting-designated-review','handoff':{'assignment_generation':1},'handoff_digest':'sha256:'+'1'*64}})); sys.exit(0)
if 'check' in args:
    sys.exit(0 if scenario in ('published','retry','recovered') else (69 if scenario in ('returned','surrendered') else 65))
sys.exit(64)
'''
for tool in ('forge-cli', 'agent-session', 'git'):
    path = bin_dir / tool
    path.write_text(stub)
    path.chmod(0o755)

def run(scenario, assigned=True):
    commands.write_text('')
    env = dict(os.environ, PATH=str(bin_dir)+os.pathsep+os.environ['PATH'],
               ROUTE_SCENARIO=scenario, ROUTE_COMMANDS=str(commands),
               PROVIDER='github', OWNER_REPO='example/project', PR_NUMBER='7', BASE_REF='origin/main',
               AGENT_SESSION_ID='worker-session', DESIGNATED_REVIEW_AUTHOR='review-app[bot]',
               REVIEW_HANDOFF_BODY_FILE='handoff.md')
    env.pop('AGENT_REVIEWER_SESSION', None)
    if assigned: env['AGENT_REVIEWER_SESSION']='reviewer-session@review-machine'
    result = subprocess.run(['bash','-c',block],env=env,capture_output=True,text=True)
    return result.returncode, commands.read_text()

status, calls = run('published', False)
assert status == 0 and calls == '', (status, calls)
status, calls = run('old-cli')
assert status == 69 and 'message send' not in calls and ' check ' not in calls, (status, calls)
for scenario, expected in [('initial',65),('stale',65),('published',0),('recovered',0)]:
    status, calls = run(scenario)
    assert status == expected, (scenario,status,calls)
    assert 'message send' in calls, (scenario,calls)
    assert '--expected-head '+ 'a'*40 in calls, calls
    assert (' assign ' in calls) == (scenario=='initial'), calls
    assert calls.index(' inspect ') < calls.index('message send') < calls.index(' check '), calls
    assert '--review-author review-app[bot]' in calls, calls
    assert '--base-sha '+ 'b'*40 not in calls, calls
    generation=2 if scenario=='recovered' else 1
    assert '--idempotency-key review-handoff-sha256:'+str(generation)*64+'-'+'a'*40 in calls, calls
for scenario, expected in [('returned',69),('surrendered',69),('conflict',65)]:
    status,calls=run(scenario)
    assert status == expected and 'message send' not in calls and ' assign ' not in calls, (scenario,status,calls)
status, calls = run('mailbox-failure')
assert status == 1 and ' check ' not in calls, (status,calls)
status, calls = run('retry')
assert status == 0 and 'message send' in calls and ' assign ' not in calls, (status,calls)
_, first=run('published')
_, second=run('recovered')
first_key=next(line.split('--idempotency-key ')[1] for line in first.splitlines() if 'message send' in line)
second_key=next(line.split('--idempotency-key ')[1] for line in second.splitlines() if 'message send' in line)
assert first_key != second_key, (first_key,second_key)
_, replay=run('published')
assert replay==first, (replay,first)
print('designated route: unassigned, old CLI, provider base, ownership states, generation keys and retry passed')

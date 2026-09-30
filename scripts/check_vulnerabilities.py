#!/usr/bin/env python3
"""Fail closed for high/critical vulnerabilities; exemptions require reason and expiry."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

report=json.loads(Path(sys.argv[1]).read_text())
assert 'Results' in report and isinstance(report['Results'],list), 'Malformed scanner report'
waivers=json.loads(Path('security/vulnerability-waivers.json').read_text())
valid=set()
for waiver in waivers:
    assert waiver['reason'].strip(), 'Empty exemption reason'
    expiry=datetime.fromisoformat(waiver['expiresAt'].replace('Z','+00:00'))
    assert expiry.tzinfo is not None and expiry>datetime.now(timezone.utc), 'Expired/invalid exemption'
    valid.add((waiver['id'],waiver['package'],waiver['installedVersion']))
failures=[]
for result in report.get('Results',[]):
    if result.get('Secrets'):
        raise SystemExit('Credential findings in container image; release blocked (values redacted).')
    for v in result.get('Vulnerabilities',[]):
        if v['Severity'] in {'HIGH','CRITICAL'} and (v['VulnerabilityID'],v['PkgName'],v['InstalledVersion']) not in valid:
            failures.append({'id':v['VulnerabilityID'],'package':v['PkgName'],'severity':v['Severity']})
if failures:
    print(json.dumps(failures,indent=2))
    raise SystemExit(1)
print('No unwaived high/critical vulnerabilities.')

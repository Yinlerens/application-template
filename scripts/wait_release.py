#!/usr/bin/env python3
"""Fail the release unless its public API and real database write become healthy."""
import json, os, time, urllib.request, urllib.error
version=os.environ['GITHUB_SHA']
base=os.environ.get('RELEASE_URL','https://acceptance.apps.makima.sbs').rstrip('/')
deadline=time.monotonic()+900
while time.monotonic()<deadline:
    try:
        with urllib.request.urlopen(base+'/api',timeout=15) as r:
            data=json.load(r);assert r.status==200 and data['version']==version
        with urllib.request.urlopen(urllib.request.Request(base+'/api/db',method='POST'),timeout=15) as r:
            assert r.status==200 and r.headers['x-release-version']==version and json.load(r)['events']>0
        print('Expected release responds over trusted HTTPS and completes a database write.')
        break
    except (urllib.error.URLError,TimeoutError,AssertionError,KeyError,json.JSONDecodeError):time.sleep(15)
else:raise SystemExit('Release did not become healthy within 15 minutes; inspect Argo and workload events.')

#!/usr/bin/env python3
"""Release-only content write; no credentials in git URLs or subprocess arguments."""
import base64
import json
import os
import urllib.request
import yaml

token=os.environ['FOUNDATION_TOKEN']
url='https://api.github.com/repos/Yinlerens/cloud-foundation/contents/clusters/production/applications/acceptance/values.yaml'
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json'}
with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as r:old=json.load(r)
values=yaml.safe_load(base64.b64decode(old['content']))
values['image']={'repository':os.environ['IMAGE'],'digest':os.environ['IMAGE_DIGEST'],
                 'pullPolicy':'IfNotPresent','pullSecret':'ghcr-pull'}
values['releaseVersion']=os.environ['GITHUB_SHA']
body={'message':'Deploy verified application '+os.environ['GITHUB_SHA'][:12],
      'content':base64.b64encode(yaml.safe_dump(values,sort_keys=False).encode()).decode(),'sha':old['sha']}
with urllib.request.urlopen(urllib.request.Request(url,headers=headers,method='PUT',data=json.dumps(body).encode()),timeout=30) as r:assert r.status in {200,201}
print('Verified image recorded in GitOps; awaiting deployed version and business smoke test.')

import os,base64,yaml
from publish_validated import api,publish,REPO
name=os.environ.get('APP_NAME','acceptance');path=f'clusters/production/applications/{name}/values.yaml'
base=api('GET',f'/repos/{REPO}/git/ref/heads/main')['object']['sha']
body=api('GET',f'/repos/{REPO}/contents/{path}?ref={base}');v=yaml.safe_load(base64.b64decode(body['content']))
v['image']={'repository':os.environ['IMAGE'],'digest':os.environ.get('DIGEST') or os.environ['IMAGE_DIGEST'],'pullPolicy':'IfNotPresent','pullSecret':'ghcr-pull'};v['releaseVersion']=os.environ['GITHUB_SHA']
publish({path:yaml.safe_dump(v,sort_keys=False)},'Release '+name+' '+v['releaseVersion'][:12],base)

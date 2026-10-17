"""Pin upstream HEAD, skip already published inputs, and generate a PKGBUILD."""
import argparse,base64,hashlib,json,os,pathlib,re,shlex,time
import urllib.error,urllib.parse,urllib.request

HERE=pathlib.Path(__file__).resolve().parent
API='https://api.github.com/'
UPSTREAM='genspark-ai/genoffice'
APP='genoffice'

def request(url,accept='application/vnd.github+json'):
    headers={'Accept':accept,'User-Agent':'genoffice-archlinux-workflow'}
    if url.startswith(API) and os.environ.get('GH_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt==3:raise
        except (TimeoutError,urllib.error.URLError):
            if attempt==3:raise
        time.sleep(2**attempt)
    raise RuntimeError('Unreachable request')

def api(path):return json.loads(request(API+path))

def content(repo,path,sha):
    value=api(f'repos/{repo}/contents/{path}?ref={sha}')
    return base64.b64decode(value['content']).decode()

def releases(repo):
    page=1
    while True:
        values=api(f'repos/{repo}/releases?per_page=100&page={page}')
        yield from values
        if len(values)<100:break
        page+=1

def previous(repo):
    for release in releases(repo):
        if release['draft']:continue
        asset=next((x for x in release['assets'] if x['name']=='upstream.json'),None)
        if asset:
            state=json.loads(request(asset['url'],'application/octet-stream'))
            if state.get('app')!=APP:raise ValueError('Incorrect release state')
            if not any(x['name']==state.get('package') for x in release['assets']):
                raise ValueError('Incomplete published release')
            return state
    return None

def recipe_hash():
    h=hashlib.sha256()
    for name in ('PKGBUILD.in','install.sh.in','build.sh','validate.py'):
        h.update(name.encode());h.update((HERE/name).read_bytes())
    return h.hexdigest()

def same_inputs(old,new):
    return old is not None and all(old.get(k)==new.get(k) for k in ('commit','recipe_sha256'))

def pkgversion(version,stamp,sha):
    # Timestamp comes from the commit, not this workflow run, for deterministic rebuilds.
    base=re.sub(r'[^A-Za-z0-9.+_]','.',version)
    date=re.sub(r'[^0-9]','',stamp)[:14]
    return f'{base}.r{date}.g{sha[:12]}'

def changes(repo,base,head):
    result=[];page=1
    while True:
        data=api(f'repos/{repo}/compare/{base}...{head}?per_page=100&page={page}')
        commits=data.get('commits',[])
        result.extend(f"- {x['commit']['message']}\n  {x['html_url']}" for x in commits)
        if len(commits)<100:break
        page+=1
    return '\n\n'.join(result)

def notes(repo,sha,old):
    if old:
        text=changes(repo,old['commit'],sha)
        return text or f'https://github.com/{repo}/commit/{sha}\n'
    try:release=api(f'repos/{repo}/releases/latest')
    except urllib.error.HTTPError as error:
        if error.code!=404:raise
        release=None
    if release:
        text=release.get('body') or release['html_url']
        tag=release['tag_name']
        extra=changes(repo,tag,sha)
        return text+('\n\n'+extra if extra else '')+'\n'
    commits=api(f'repos/{repo}/commits?sha={sha}&per_page=100')
    return '\n\n'.join(f"- {x['commit']['message']}\n  {x['html_url']}" for x in reversed(commits))+'\n'

def download_archive(repo,sha,directory,name):
    url=f'https://codeload.github.com/{repo}/tar.gz/{sha}'
    path=directory/name
    data=request(url);path.write_bytes(data)
    return f'{name}::{url}',hashlib.sha256(data).hexdigest()

def output(values):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as stream:
            for key,value in values.items():stream.write(f'{key}={value}\n')
    print(json.dumps(values))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repository',default=os.environ.get('GITHUB_REPOSITORY','zamkara/genoffice'))
    parser.add_argument('--directory',required=True)
    args=parser.parse_args()
    directory=pathlib.Path(args.directory);directory.mkdir(parents=True,exist_ok=True)
    info=api(f'repos/{UPSTREAM}')
    commit=api(f'repos/{UPSTREAM}/commits/{urllib.parse.quote(info["default_branch"],safe="")}')
    sha=commit['sha']
    shell_pkg=json.loads(content(UPSTREAM,'apps/shell/package.json',sha))
    version=str(shell_pkg['version'])
    description='AI-native office suite for Docs, Sheets, Slides, PDF, Markdown, and HTML'
    state={
        'app':APP,
        'upstream':UPSTREAM,
        'branch':info['default_branch'],
        'commit':sha,
        'version':version,
        'commit_date':commit['commit']['committer']['date'],
        'recipe_sha256':recipe_hash(),
        'architecture':'x86_64',
        'binary':APP,
        'app_id':'com.genoffice.app',
    }
    old=previous(args.repository)
    if same_inputs(old,state):
        output({'changed':'false','app':APP});return
    pkgver=pkgversion(version,state['commit_date'],sha)
    pkgrel=old.get('pkgrel',1)+1 if old and old.get('pkgver')==pkgver else 1
    tag=f'{APP}-{pkgver}-{pkgrel}'
    state.update(pkgver=pkgver,pkgrel=pkgrel,previous_commit=old['commit'] if old else None)
    source,checksum=download_archive(UPSTREAM,sha,directory,f'{APP}-{sha}.tar.gz')
    replacements={
        'PKGVER':pkgver,
        'PKGREL':str(pkgrel),
        'DESCRIPTION':shlex.quote(description),
        'URL':shlex.quote('https://github.com/'+UPSTREAM),
        'SHA':sha,
        'UPSTREAM_VERSION':shlex.quote(version),
        'BUILD_DATE':state['commit_date'][:10],
        'SOURCES':shlex.quote(source),
        'CHECKSUMS':shlex.quote(checksum),
        'RELEASE_TAG':tag,
    }
    recipe=(HERE/'PKGBUILD.in').read_text()
    installer=(HERE/'install.sh.in').read_text()
    for key,value in replacements.items():
        recipe=recipe.replace('@'+key+'@',value)
        installer=installer.replace('@'+key+'@',value)
    (directory/'PKGBUILD').write_text(recipe)
    install_path=directory/'install.sh'
    install_path.write_text(installer)
    install_path.chmod(0o755)
    (directory/'upstream.json').write_text(json.dumps(state,indent=2)+'\n')
    (directory/'CHANGELOG.md').write_text(notes(UPSTREAM,sha,old))
    output({'changed':'true','app':APP,'tag':tag,'pkgver':pkgver,'recipe':state['recipe_sha256']})

if __name__=='__main__':main()

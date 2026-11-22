"""Build the reviewed static site without publishing superseded topic HTML."""
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import json,re,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist';cfg=json.loads((ROOT/'scripts/criteria-consolidation.json').read_text());redirects={k.rstrip('/'):v for k,v in cfg['redirects'].items()};origin='https://www.buyingwealthbook.com'
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
skip={'.git','.vercel','node_modules','dist','scripts','tests','__pycache__'}
retired={p.strip('/')+'/index.html' for p in redirects}
for p in ROOT.rglob('*'):
 rel=p.relative_to(ROOT)
 if not p.is_file() or any(part in skip or part.startswith('.') for part in rel.parts) or rel.as_posix() in retired:continue
 if p.suffix.lower() not in {'.html','.css','.js','.json','.svg','.txt','.xml','.png','.jpg','.jpeg','.webp','.avif','.ico','.woff','.woff2','.csv'}:continue
 if rel.as_posix() in {'vercel.json'}:continue
 dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
def normalize(value):
 if not (value.startswith('/') and not value.startswith('//') or value.startswith(origin+'/')):return value
 u=urlsplit(value);path=u.path
 if path.endswith('/index.html'):path=path[:-11]
 path=path.rstrip('/')
 if path not in redirects:return value
 d=urlsplit(redirects[path]);return urlunsplit((u.scheme,u.netloc,d.path,u.query,d.fragment))
changed=[]
for p in OUT.rglob('*.html'):
 s=p.read_text();n=re.sub(r'\b(href|content)=(["\'])([^"\']*)\2',lambda m:m[1]+'='+m[2]+normalize(m[3])+m[2],s)
 def rewrite_json(m):
  d=json.loads(m[2])
  def visit(x):
   if isinstance(x,str):return normalize(x)
   if isinstance(x,list):return [visit(v) for v in x]
   if isinstance(x,dict):return {k:visit(v) for k,v in x.items()}
   return x
  n=visit(d)
  return m[1]+json.dumps(n,separators=(',',':'))+m[3] if n!=d else m[0]
 n=re.sub(r'(<script[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',rewrite_json,n,flags=re.S)
 n=n.replace('Browse all 100 guides','Browse the learning library')
 if n!=s:p.write_text(n);changed.append(str(p.relative_to(OUT)))
platform=json.loads((ROOT/'vercel.json').read_text());assert platform['cleanUrls'] is False
rewrites={x['source']:x['destination'] for x in platform['rewrites']};owners=[x.text for x in ET.parse(OUT/'sitemap.xml').iter() if x.tag.endswith('loc')]
assert len(owners)==316
for u in owners:
 route=urlsplit(u).path;physical=rewrites[route];assert '..' not in physical and (OUT/physical.lstrip('/')).is_file()
 assert re.search(r'<link\b[^>]*rel="canonical"[^>]*href="'+re.escape(u)+'"', (OUT/physical.lstrip('/')).read_text())
for rel in retired:assert not (OUT/rel).exists() and (ROOT/rel).is_file()
print(json.dumps({'owners':len(owners),'retiredPublishedCopiesOmitted':len(retired),'linkOrFooterRewrittenPages':len(changed)}))

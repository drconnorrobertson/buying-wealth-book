"""Reject conflicting canonical hosts or sitemap URLs before publication."""
from pathlib import Path
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
HOST = 'www.buyingwealthbook.com'
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.canonicals = []; self.noindex = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonicals.append(a.get('href', ''))
        if tag == 'meta' and a.get('name', '').lower() == 'robots':
            self.noindex = 'noindex' in a.get('content', '').lower()
errors = []; canonical_urls = set(); pages = 0
for path in ROOT.rglob('*.html'):
    if '.git' in path.parts or path.name.startswith('google') or path.name == '404.html':
        continue
    page = Page(); page.feed(path.read_text()); pages += 1
    if page.noindex:
        continue
    if len(page.canonicals) != 1:
        errors.append(f'{path.relative_to(ROOT)}: expected one canonical'); continue
    url = page.canonicals[0]; parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != HOST:
        errors.append(f'{path.relative_to(ROOT)}: conflicting canonical {url}')
    if parsed.path not in ('', '/') and not parsed.path.endswith('/'):
        errors.append(f'{path.relative_to(ROOT)}: missing canonical trailing slash')
    canonical_urls.add(url)
locs = [e.text.strip() for e in ET.parse(ROOT / 'sitemap.xml').iter() if e.tag.endswith('}loc')]
for url in locs:
    if url not in canonical_urls:
        errors.append(f'Sitemap URL is not an indexable page canonical: {url}')
if len(locs) != len(set(locs)):
    errors.append('Duplicate sitemap URLs')
if f'Sitemap: https://{HOST}/sitemap.xml' not in (ROOT / 'robots.txt').read_text():
    errors.append('Robots sitemap host conflict')
if errors:
    raise SystemExit('\n'.join(errors[:30]))
print(f'Indexing checks passed: {pages} HTML pages; {len(locs)} canonical sitemap URLs; one HTTPS host.')

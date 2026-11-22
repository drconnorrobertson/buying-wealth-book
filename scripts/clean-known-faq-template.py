"""Remove the unsupported legacy FAQ template, then validate published FAQ text."""
from pathlib import Path
from html.parser import HTMLParser
import html,json,re,sys,xml.etree.ElementTree as ET

root=Path(sys.argv[1]).resolve()
owners={e.text.strip() for e in ET.parse(root/'sitemap.xml').iter() if e.tag.endswith('}loc')}
legacy_answers={
    'Use the current source records and identify the decision owner before relying on the answer.',
    'Document the assumption, evidence, downside case, and next review date in the same decision file.',
    'Escalate fact-specific legal, tax, financing, insurance, or technical questions to a qualified advisor.'
}
class Visible(HTMLParser):
    def __init__(self):super().__init__();self.hidden=0;self.text=[];self.canonical=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style'):self.hidden+=1
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden-=1
    def handle_data(self,text):
        if not self.hidden:self.text.append(text)
def normalize(text):return ' '.join(html.unescape(text).split()).casefold()
pattern=re.compile(r'(<script[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',re.S)
changed=[];retained=0;errors=[];seen=set()
for file in sorted(root.rglob('*.html')):
    if any(p in ('.git','node_modules','dist') for p in file.relative_to(root).parts):continue
    source=file.read_text();page=Visible();page.feed(source)
    if page.canonical not in owners:continue
    seen.add(page.canonical);visible=normalize(' '.join(page.text));removed=[0]
    def supported(node):
        return all(normalize(q.get('name','')) in visible and normalize(q.get('acceptedAnswer',{}).get('text','')) in visible for q in node.get('mainEntity',[]))
    def clean(node):
        global retained
        if isinstance(node,list):return [result for value in node if (result:=clean(value)) is not None]
        if not isinstance(node,dict):return node
        if node.get('@type')=='FAQPage':
            if supported(node):retained+=1;return node
            answers=[q.get('acceptedAnswer',{}).get('text','') for q in node.get('mainEntity',[])]
            if len(answers)==3 and set(answers)==legacy_answers:removed[0]+=1;return None
            errors.append(str(file.relative_to(root))+': unsupported non-template FAQ content');return node
        return {key:clean(value) if key=='@graph' else value for key,value in node.items()}
    def replace(match):
        original=json.loads(match[2]);updated=clean(original)
        if updated==original:return match[0]
        return match[1]+json.dumps(updated,separators=(',',':'))+match[3] if updated is not None else ''
    updated=pattern.sub(replace,source)
    if updated!=source:
        assert pattern.sub('',source)==pattern.sub('',updated),'Visible HTML changed'
        file.write_text(updated);changed.append(str(file.relative_to(root)))
assert seen==owners,'Some sitemap owners are missing from output HTML'
print(json.dumps({'publishedOwners':len(owners),'removedLegacyFAQNodes':len(changed),'retainedVisibleFAQNodes':retained,'errors':errors,'changedHTML':changed}))
if errors:raise SystemExit('FAQ questions and answers must match visible page text.')

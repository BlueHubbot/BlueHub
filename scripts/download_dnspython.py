import os
import re
import ssl
import urllib.request
from html.parser import HTMLParser

ctx = ssl._create_unverified_context()
resp = urllib.request.urlopen('https://pypi.org/simple/dnspython/', context=ctx)
html = resp.read().decode('utf-8')

class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs) -> None:
        for name, value in attrs:
            if name == 'href':
                self.links.append(value)

parser = LinkParser()
parser.feed(html)

whls = []
for l in parser.links:
    base = l.split('#')[0]
    name_part = base.split('/')[-1]
    if not base.endswith('.whl'):
        continue
    if 'rc' in name_part.lower() or 'dev' in name_part.lower():
        continue
    # Skip non-stable pre-release suffixes (like a1, b1, etc.)
    if re.search(r'dnspython-\d+\.\d+\.\d+[a-z]', name_part):
        continue
    match = re.search(r'dnspython-([\d]+(?:\.\d+)*)', name_part)
    if match:
        version_str = match.group(1)
        whls.append((version_str, l))

if whls:
    def sort_key(item):
        parts = item[0].split('.')
        try:
            return tuple(int(x) for x in parts)
        except ValueError:
            return (0,)

    whls.sort(key=sort_key)
    latest_ver, latest_url = whls[-1]
    print(f"Latest version: {latest_ver}")
    print(f"URL: {latest_url}")

    print("\nDownloading...")
    resp2 = urllib.request.urlopen(latest_url, context=ctx)
    os.makedirs('_packages', exist_ok=True)

    url_base = latest_url.split('#')[0]
    orig_fname = url_base.split('/')[-1]
    fname = os.path.join('_packages', orig_fname)

    with open(fname, 'wb') as f:
        while True:
            chunk = resp2.read(8192)
            if not chunk:
                break
            f.write(chunk)
    size = os.path.getsize(fname) / 1024
    print(f"Saved: {fname} ({size:.1f} KB)")
else:
    print("No suitable versions found!")
    for l in parser.links:
        base = l.split('#')[0]
        print(f"  {base.split('/')[-1]}")

import os
import re
import ssl
import urllib.request
from html.parser import HTMLParser

ctx = ssl._create_unverified_context()
resp = urllib.request.urlopen('https://pypi.org/simple/email-validator/', context=ctx)
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

# Collect wheel files (strip hash fragments)
whls = []
for l in parser.links:
    base = l.split('#')[0]
    name_part = base.split('/')[-1]
    # Must be a .whl file, non-rc, and match email_validator- pattern
    if not base.endswith('.whl'):
        continue
    if 'rc' in name_part.lower() or 'dev' in name_part.lower():
        continue
    # Extract version
    match = re.search(r'email_validator-([\d]+(?:\.\d+)*)', name_part)
    if match:
        version_str = match.group(1)
        whls.append((version_str, l))

if not whls:
    # Fall back to tar.gz
    tars = []
    for l in parser.links:
        base = l.split('#')[0]
        name_part = base.split('/')[-1]
        if not base.endswith('.tar.gz'):
            continue
        if 'rc' in name_part.lower() or 'dev' in name_part.lower():
            continue
        match = re.search(r'email_validator-([\d.]+)', name_part)
        if match:
            tars.append((match.group(1), l))
    whls = tars

if whls:
    # Sort by version tuple
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

    # Determine extension and filename from URL
    url_base = latest_url.split('#')[0]
    ext = '.whl' if url_base.endswith('.whl') else '.tar.gz'
    # Use the original filename from the URL (with hyphens, not underscores)
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
        print(f"  {l}")

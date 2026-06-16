import os
import re
import ssl
import urllib.request

ctx = ssl._create_unverified_context()
resp = urllib.request.urlopen('https://pypi.org/simple/email-validator/', context=ctx)
html = resp.read().decode()

# Find all links containing email_validator with tar.gz
links = re.findall(r'href="([^"]+email_validator[^"]+tar\.gz)"', html)
print(f"Found {len(links)} tar.gz links")

# Filter for latest non-rc version
versions = []
for link in links:
    match = re.search(r'email_validator-([\d.]+)\.tar\.gz', link)
    if match and 'rc' not in match.group(0).lower() and 'a' not in match.group(0).lower():
        try:
            ver = tuple(int(x) for x in match.group(1).split('.'))
            versions.append((ver, link))
        except ValueError:
            pass

if versions:
    versions.sort()
    latest_url = versions[-1][1]
    if latest_url.startswith('/'):
        latest_url = 'https://pypi.org' + latest_url

    print(f"Downloading: {latest_url}")
    resp2 = urllib.request.urlopen(latest_url, context=ctx)
    os.makedirs('_packages', exist_ok=True)
    fname = os.path.join('_packages', 'email_validator_latest.tar.gz')
    with open(fname, 'wb') as f:
        while True:
            chunk = resp2.read(8192)
            if not chunk:
                break
            f.write(chunk)
    print(f"Saved to: {fname} ({os.path.getsize(fname)} bytes)")
else:
    print("No suitable versions found")
    # Debug: print all links
    for link in links[:5]:
        print(f"  Link: {link}")

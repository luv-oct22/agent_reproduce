"""Verify vendored lab assets; optionally restore missing files from their sources."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Check local files without network access')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / 'assets'
    entries = json.loads((root / 'manifest.json').read_text())['files']
    for entry in entries:
        path = root / entry['path']
        if not path.exists() and not args.verify:
            request = Request(entry['url'], headers={'User-Agent': 'robotics-lab-asset-fetcher/1.0'})
            with urlopen(request, timeout=90) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != entry['sha256']:
                raise ValueError(f'Upstream content changed: {entry["url"]}; refusing unverified asset')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Missing or modified asset: {path}')
    print(f'Verified {len(entries)} assets against SHA-256 manifest.')


if __name__ == '__main__':
    main()

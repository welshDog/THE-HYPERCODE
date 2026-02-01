import json
import os
import sys

def main():
    path = os.getenv('MANIFEST_PATH', 'bundle-manifest.json')
    with open(path, 'r', encoding='utf-8') as f:
        m = json.load(f)
    files = [i['file'] for i in m.get('items', [])]
    js = [f for f in files if f.endswith('.js')]
    css = [f for f in files if f.endswith('.css')]
    if not js or not css:
        print('Compatibility check failed: missing js or css assets')
        sys.exit(1)
    print('Compatibility check passed')

if __name__ == '__main__':
    main()

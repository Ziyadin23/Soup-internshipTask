"""Check gated-file access without downloading data or printing credentials."""
import os
from pathlib import Path

import requests
from huggingface_hub import get_token


def main():
    env = Path(__file__).resolve().parents[1] / '.env'
    if env.is_file():
        for line in env.read_text().splitlines():
            if line.startswith('HF_TOKEN='):
                os.environ.setdefault('HF_TOKEN', line.split('=', 1)[1].strip())
    token = get_token()
    if not token:
        print('No Hugging Face credential configured. Run scripts/access_wizard.sh.')
        return 3
    url = ('https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k/'
           'resolve/26d14ebfe18b1f7b524bd39b404b50af5dc97866/xlam_function_calling_60k.json')
    try:
        r = requests.head(url, headers={'Authorization': f'Bearer {token}'},
                          allow_redirects=False, timeout=20)
    except requests.RequestException:
        print('Hugging Face connection failed; credential contents were not logged.')
        return 1
    print(f'xLAM access HTTP {r.status_code}; credential contents were not logged.')
    if r.status_code in (200, 302, 303, 307):
        print('Dataset access is available.')
        return 0
    print('Check token read permissions and accept the dataset conditions in your account.')
    return 3


if __name__ == '__main__':
    raise SystemExit(main())

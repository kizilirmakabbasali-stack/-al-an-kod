import re
import sys
from pathlib import Path

def parse_symbols(text: str):
    lines = text.splitlines()
    out = []
    for line in lines:
        s = (line or '').strip().upper()
        if not s:
            continue
        # Skip single letters/markers and category tags
        if s in {'G', 'D', 'REIT', 'CEF'}:
            continue
        # Ignore obvious Turkish full names (contain space or non-ascii letters)
        # but keep pure tickers like THYAO, ASELS, ALBRK, etc.
        # A ticker is 2-6 uppercase alnum characters, no spaces
        if re.fullmatch(r'[A-Z0-9]{2,6}', s):
            out.append(s)
    # dedupe and sort
    return sorted(list(set(out)))


def main():
    raw_path = Path('raw_bist_list.txt')
    if not raw_path.exists():
        print('raw_bist_list.txt not found.')
        sys.exit(1)
    text = raw_path.read_text(encoding='utf-8', errors='ignore')
    syms = parse_symbols(text)
    # Write to bist_tickers.txt
    out_path = Path('bist_tickers.txt')
    header = '# Auto-generated from raw_bist_list.txt by tools/parse_tickers.py\n'
    out_path.write_text(header + '\n'.join(syms) + '\n', encoding='utf-8')
    print(f'Parsed {len(syms)} symbols -> {out_path}')

if __name__ == '__main__':
    main()

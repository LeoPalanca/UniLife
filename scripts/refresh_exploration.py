"""Refresh descriptive country/university exploration from an official annual KA1 release."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from erasmusgravity.dashboard.refresh import build_refresh
from build_dashboard import render_dashboard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--annex', type=Path, default=Path('data/raw/annual-report-2024-statistical-annex.xlsx'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    payload = build_refresh(args.snapshot, args.source, args.year, args.cache, args.annex)
    output = render_dashboard(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(output)
    temporary.replace(args.output)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(payload['explorationMeta'], indent=2) + '\n')
    print(json.dumps(payload['explorationMeta'], indent=2))


if __name__ == '__main__':
    main()

"""Parse cert markdown notes into H2-bounded paragraph blocks."""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def parse_file(file_path: Path, cert_name: str) -> list[dict]:
    source_type = "labs" if "_labs" in file_path.stem else "notes"
    h1, h2 = "Introduction", "General"
    blocks = []
    chunk_index = 0

    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("###"):
            continue
        if stripped.startswith("##"):
            h2 = stripped.lstrip("#").strip()
            continue
        if stripped.startswith("#"):
            h1 = stripped.lstrip("#").strip()
            h2 = "General"
            continue

        blocks.append({
            "cert_name": cert_name,
            "source_type": source_type,
            "source_file": file_path.name,
            "h1": h1,
            "h2": h2,
            "chunk_index": chunk_index,
            "text": stripped,
        })
        chunk_index += 1

    return blocks


def main(cert: str | None = None):
    load_dotenv()

    cert_dirs = [RAW_DIR / cert] if cert else sorted(
        d for d in RAW_DIR.iterdir() if d.is_dir()
    )

    all_blocks = []
    for cert_dir in cert_dirs:
        if not cert_dir.is_dir():
            print(f"Cert folder not found: {cert_dir}")
            continue
        for md_file in sorted(cert_dir.glob("*.md")):
            blocks = parse_file(md_file, cert_dir.name)
            print(f"{cert_dir.name}/{md_file.name}: {len(blocks)} paragraphs")
            all_blocks.extend(blocks)

    print("\nFirst 3 blocks:")
    for block in all_blocks[:3]:
        print(json.dumps(block, indent=2))

    return all_blocks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert", help="Process only this cert folder (e.g. VMF)")
    args = parser.parse_args()
    main(args.cert)

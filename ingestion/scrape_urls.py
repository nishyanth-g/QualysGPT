"""Scrape supplementary URLs from data/urls.json into paragraph blocks."""

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
URLS_JSON = ROOT / "data" / "urls.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (QualysGPT ingestion bot)"}
MAX_CHARS = 1000


def fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"Warning: failed to fetch {url}: {e}")
        return None


def extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    text = soup.get_text(separator="\n\n")
    return title, text


def split_into_segments(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    segments = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 1 > max_chars:
            segments.append(current)
            current = para
        else:
            current = f"{current}\n{para}" if current else para
    if current:
        segments.append(current)
    return segments


def scrape_entry(entry: dict) -> list[dict] | None:
    html = fetch_page(entry["url"])
    if html is None:
        return None
    title, text = extract_text(html)
    return [
        {
            "cert_name": entry["cert_name"],
            "source_type": "url",
            "source_file": entry["url"],
            "h1": title,
            "h2": entry["description"],
            "chunk_index": i,
            "text": segment,
        }
        for i, segment in enumerate(split_into_segments(text))
    ]


def scrape_all(urls_path: Path = URLS_JSON, cert: str | None = None) -> tuple[list[dict], dict[str, dict[str, int]]]:
    entries = json.loads(urls_path.read_text(encoding="utf-8"))
    if cert:
        entries = [e for e in entries if e["cert_name"] == cert]
    all_blocks = []
    stats: dict[str, dict[str, int]] = {}

    for entry in entries:
        cert_name = entry["cert_name"]
        stats.setdefault(cert_name, {"scraped": 0, "failed": 0})
        blocks = scrape_entry(entry)
        if blocks is None:
            stats[cert_name]["failed"] += 1
            continue
        stats[cert_name]["scraped"] += 1
        all_blocks.extend(blocks)

    return all_blocks, stats


def main(cert: str | None = None):
    load_dotenv()
    all_blocks, stats = scrape_all(cert=cert)

    print("\nScrape results per cert:")
    for cert_name, counts in stats.items():
        print(f"{cert_name}: {counts['scraped']} scraped, {counts['failed']} failed")
    print(f"\nTotal segments: {len(all_blocks)}")

    return all_blocks


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert", help="Process only this cert (e.g. VMDR)")
    args = parser.parse_args()
    main(args.cert)

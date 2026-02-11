"""
Download 5 samples per category from Freesound (optional).
Requires FREESOUND_API_KEY in environment or .env. If no key or rate limit,
prints instructions for manual download or URL manifest (Option B/C).
"""
import json
import os
import time
from pathlib import Path

import requests

from config import ROOT_DIR, RAW_DIR, CATEGORIES, SAMPLES_PER_CATEGORY

# Primary search queries (simple terms work better on Freesound)
CATEGORY_QUERIES = {
    "Office": "office ambience",
    "Cafe": "cafe coffee shop",
    "StreetTraffic": "traffic street",
    "Home": "home living room",
    "CallCenter": "call center",
    "Construction": "construction jackhammer",
    "Airport": "airport terminal",
}
# Fallback queries if primary returns too few (e.g. strict duration filter)
CATEGORY_QUERIES_FALLBACK = {
    "Office": ["office", "office room", "office noise"],
    "CallCenter": ["office chatter", "office phones", "indoor ambience"],
}

FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/"
FREESOUND_SOUND_URL = "https://freesound.org/apiv2/sounds/{id}/"
# Prefer duration <= 10 s; if too few results, we retry with no duration filter
DURATION_FILTER = "duration:[0 TO 10]"
FIELDS = "id,name,previews,license,username,duration"


def get_api_key() -> str | None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT_DIR / ".env")
    except ImportError:
        pass
    return os.environ.get("FREESOUND_API_KEY", "").strip() or None


def search_sounds(token: str, query: str, duration_filter: str | None, max_results: int = 10) -> list[dict]:
    params = {
        "token": token,
        "query": query,
        "fields": FIELDS,
        "page_size": max_results,
    }
    if duration_filter:
        params["filter"] = duration_filter
    r = requests.get(FREESOUND_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("results", [])


def get_preview_url(sound: dict) -> str | None:
    """Best available preview URL (prefer HQ MP3)."""
    previews = sound.get("previews") or {}
    return previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")


def download_file(url: str, path: Path, token: str) -> bool:
    r = requests.get(url, params={"token": token} if "freesound" in url else None, timeout=60, stream=True)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return True


def main() -> None:
    token = get_api_key()
    if not token:
        print("No FREESOUND_API_KEY set.")
        print("Option A: Get a free API key at https://freesound.org/apiv2/apply/ and set:")
        print("  export FREESOUND_API_KEY=your_key")
        print("  Or add FREESOUND_API_KEY=your_key to a .env file in this directory.")
        print("Option B: Maintain a sources.yaml with 5 URLs per category and download via script.")
        print("Option C: Manually download 5 WAV/MP3 files per category from Freesound (CC license),")
        print("  and place them in raw/Office/, raw/Cafe/, etc. Then run process_originals.py.")
        return

    attribution = []
    for category in CATEGORIES:
        raw_cat = RAW_DIR / category
        raw_cat.mkdir(parents=True, exist_ok=True)
        query = CATEGORY_QUERIES.get(category, category.lower())
        # Prefer short clips first; relax duration if too few, then try fallback queries
        results = search_sounds(token, query, DURATION_FILTER, max_results=SAMPLES_PER_CATEGORY + 5)
        if len(results) < SAMPLES_PER_CATEGORY:
            results = search_sounds(token, query, None, max_results=SAMPLES_PER_CATEGORY + 5)
        if len(results) < SAMPLES_PER_CATEGORY and category in CATEGORY_QUERIES_FALLBACK:
            for fallback_query in CATEGORY_QUERIES_FALLBACK[category]:
                if len(results) >= SAMPLES_PER_CATEGORY:
                    break
                more = search_sounds(token, fallback_query, None, max_results=SAMPLES_PER_CATEGORY + 5)
                # Merge, dedupe by id, keep order
                seen = {s["id"] for s in results}
                for s in more:
                    if s["id"] not in seen:
                        results.append(s)
                        seen.add(s["id"])
                time.sleep(0.3)
        collected = 0
        for s in results:
            if collected >= SAMPLES_PER_CATEGORY:
                break
            preview = get_preview_url(s)
            if not preview:
                continue
            idx = collected + 1
            ext = ".mp3"
            out_name = f"{category}_{idx:02d}{ext}"
            out_path = raw_cat / out_name
            if out_path.exists():
                collected += 1
                attribution.append({
                    "category": category,
                    "file": out_name,
                    "freesound_id": s.get("id"),
                    "name": s.get("name"),
                    "username": s.get("username"),
                    "license": s.get("license"),
                })
                continue
            try:
                download_file(preview, out_path, token)
                attribution.append({
                    "category": category,
                    "file": out_name,
                    "freesound_id": s.get("id"),
                    "name": s.get("name"),
                    "username": s.get("username"),
                    "license": s.get("license"),
                })
                collected += 1
                print(f"  {category}: {out_name} (id={s.get('id')})")
            except Exception as e:
                print(f"  Skip {s.get('id')}: {e}")
            time.sleep(0.5)
        if collected < SAMPLES_PER_CATEGORY:
            print(f"  Warning: {category} has {collected} files (wanted {SAMPLES_PER_CATEGORY})")

    out_attribution = ROOT_DIR / "attribution.json"
    with open(out_attribution, "w") as f:
        json.dump(attribution, f, indent=2)
    print(f"Attribution saved to {out_attribution}. Please credit Freesound and authors per license.")
    print("Next: run process_originals.py then generate_levels.py.")


if __name__ == "__main__":
    main()

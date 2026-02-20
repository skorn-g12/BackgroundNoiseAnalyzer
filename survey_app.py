"""
Streamlit survey app: pick a category, play noise (alone or mixed with clean speech),
choose perceived level, submit or export responses.
Uses clipped_samples/: category subdirs with noise files + voicebooking-speech.wav (clean).
Run: streamlit run survey_app.py --server.address 0.0.0.0
"""
import csv
import io
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf
import streamlit as st

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

from config import (
    CLIPPED_SAMPLES_DIR,
    CLEAN_AUDIO_PATH,
    CLEAN_SPEECH_LEVEL_DB,
    COLLECTED_RESPONSES_CSV,
)

LABELS = ["very_low", "low", "medium", "high", "very_high"]
AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac")
TARGET_SR = 16000
EPS = np.finfo(float).eps
NOISE_LEVELS_DB = [-10, -15, -20, -25, -30, -35, -40]  # -10 to -40 dB, step 5
SAMPLES_PER_CATEGORY = 2
CROSSFADE_SEC = 0.2  # fade-out / fade-in duration when looping short noise


def load_mono(path: Path, sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """Load audio as mono float64, resampled to sr."""
    audio, file_sr = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if HAS_LIBROSA and file_sr != sr:
        audio = librosa.resample(audio.astype(np.float64), orig_sr=file_sr, target_sr=sr)
    elif file_sr != sr:
        audio = audio.astype(np.float64)
    return audio.astype(np.float64), sr


def rms_dbfs(audio: np.ndarray) -> float:
    rms = (audio.astype(np.float64) ** 2).mean() ** 0.5
    return float(20 * np.log10(rms + EPS))


def normalize_to_db(audio: np.ndarray, target_db: float) -> np.ndarray:
    rms = (audio.astype(np.float64) ** 2).mean() ** 0.5
    if rms <= 0:
        return audio
    scale = 10 ** (target_db / 20) / (rms + EPS)
    return (audio * scale).astype(np.float32)


def extend_noise_with_crossfade(
    noise: np.ndarray, target_len: int, sr: int, crossfade_sec: float = CROSSFADE_SEC
) -> np.ndarray:
    """
    Loop noise to reach target_len. Uses 0.2s crossfade at each loop point:
    last crossfade_sec of current block fades out while first crossfade_sec of
    next block fades in, overlap-added to avoid clicks (industry standard).
    """
    n = len(noise)
    if n >= target_len:
        return noise[:target_len].astype(np.float64)
    cf = int(crossfade_sec * sr)
    cf = min(cf, n // 2, max(1, (n - 1) // 2))  # need enough samples for crossfade
    if cf < 1:
        # Fallback: simple tile (may click)
        repeats = (target_len // n) + 1
        return np.tile(noise, repeats)[:target_len].astype(np.float64)

    out = np.zeros(target_len, dtype=np.float64)
    pos = 0
    first = True
    while pos < target_len:
        if first:
            # First block: add full noise
            add_len = min(n, target_len)
            out[pos : pos + add_len] = noise[:add_len]
            pos += add_len
            first = False
        else:
            # Overlap region: fade-out (from end of prev in-place) + fade-in (from start of noise)
            # Prev block ends at pos; its tail is out[pos-cf:pos]
            # We overwrite that region with crossfade: out[pos-cf:pos] * linspace(1,0) + noise[:cf] * linspace(0,1)
            fade_out = np.linspace(1, 0, cf, dtype=np.float64)
            fade_in = np.linspace(0, 1, cf, dtype=np.float64)
            overlap_len = min(cf, target_len - (pos - cf))
            if overlap_len <= 0:
                break
            prev_tail = out[pos - cf : pos - cf + overlap_len].copy()
            next_head = noise[:overlap_len]
            out[pos - cf : pos - cf + overlap_len] = prev_tail * fade_out[:overlap_len] + next_head * fade_in[:overlap_len]
            pos = pos - cf + overlap_len
            if pos >= target_len:
                break
            # Add rest of noise (non-overlap part)
            rest_len = min(n - cf, target_len - pos)
            if rest_len > 0:
                out[pos : pos + rest_len] = noise[cf : cf + rest_len]
                pos += rest_len
    return out


def mix_clean_and_noise(
    clean_path: Path,
    noise_path: Path,
    noise_level_db: float,
    clean_level_db: float = CLEAN_SPEECH_LEVEL_DB,
) -> tuple[bytes, float]:
    """Mix clean speech + noise at given noise level. Return (wav_bytes, snr_db)."""
    clean, sr = load_mono(clean_path)
    noise, _ = load_mono(noise_path, sr)
    noise_norm = normalize_to_db(noise, noise_level_db)
    # If noise is shorter than clean, loop it with crossfade
    if len(noise_norm) < len(clean):
        noise_norm = extend_noise_with_crossfade(noise_norm, len(clean), sr)
    else:
        noise_norm = noise_norm[: len(clean)]
    clean_norm = normalize_to_db(clean, clean_level_db)
    # SNR = clean_level - noise_level (in dB)
    snr_db = clean_level_db - noise_level_db
    mixed = clean_norm.astype(np.float64) + noise_norm.astype(np.float64)
    mixed = np.clip(mixed, -1.0, 1.0).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, mixed, sr, format="WAV")
    buf.seek(0)
    return buf.read(), snr_db


def noise_to_wav_bytes(noise_path: Path, level_db: float) -> bytes:
    """Load noise, normalize to level_db, return WAV bytes."""
    noise, sr = load_mono(noise_path)
    noise_norm = normalize_to_db(noise, level_db)
    buf = io.BytesIO()
    sf.write(buf, noise_norm, sr, format="WAV")
    buf.seek(0)
    return buf.read()


def scan_clipped_samples() -> list[dict]:
    """
    Return list of {category, clip_id, path, filename, level_db} from clipped_samples.
    Uses only SAMPLES_PER_CATEGORY samples per category; each sample has NOISE_LEVELS_DB variants.
    """
    if not CLIPPED_SAMPLES_DIR.exists():
        return []
    rows = []
    for subdir in sorted(CLIPPED_SAMPLES_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        category = subdir.name
        paths = sorted(
            p for p in subdir.iterdir()
            if p.suffix.lower() in (e.lower() for e in AUDIO_EXTENSIONS)
        )[:SAMPLES_PER_CATEGORY]
        for path in paths:
            for level_db in NOISE_LEVELS_DB:
                clip_id = f"{category}/{path.name}/{level_db}"
                rows.append({
                    "category": category,
                    "clip_id": clip_id,
                    "path": path,
                    "filename": path.name,
                    "level_db": level_db,
                })
    return rows


def get_categories(rows: list) -> list[str]:
    return sorted({r["category"] for r in rows})


def get_clips_for_category(rows: list, category: str) -> list[dict]:
    return [r for r in rows if r["category"] == category]


def append_responses_to_file(respondent_id: str, votes: dict, clip_rows: list) -> bool:
    clip_lookup = {r["clip_id"]: r for r in clip_rows}
    rows = []
    for cid, label in votes.items():
        if cid not in clip_lookup:
            continue
        r = clip_lookup[cid]
        rows.append({
            "respondent_id": respondent_id,
            "clip_id": cid,
            "label": label,
            "category": r["category"],
            "level_db": r["level_db"],
        })
    if not rows:
        return False
    path = Path(COLLECTED_RESPONSES_CSV)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
        with open(path, "a", newline="") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                need_header = path.stat().st_size == 0
                w = csv.DictWriter(f, fieldnames=["respondent_id", "clip_id", "label", "category", "level_db"])
                if need_header:
                    w.writeheader()
                w.writerows(rows)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except ImportError:
        with open(path, "a", newline="") as f:
            need_header = path.stat().st_size == 0
            w = csv.DictWriter(f, fieldnames=["respondent_id", "clip_id", "label", "category", "level_db"])
            if need_header:
                w.writeheader()
            w.writerows(rows)
    return True


def main():
    st.set_page_config(page_title="Background noise level survey", layout="wide")
    st.title("Background noise level survey")
    st.markdown("Pick a category, listen to each noise clip (alone or mixed with clean speech), and choose the perceived loudness.")

    if "votes" not in st.session_state:
        st.session_state["votes"] = {}

    clip_rows = scan_clipped_samples()
    if not clip_rows:
        st.error("No clips found in clipped_samples/. Add category subdirs with .wav/.mp3/.flac files.")
        return

    categories = get_categories(clip_rows)
    if not categories:
        st.error("No categories found.")
        return

    # --- Clean audio at top ---
    st.subheader("Reference clean speech (optional)")
    if CLEAN_AUDIO_PATH.exists():
        st.audio(str(CLEAN_AUDIO_PATH))
    else:
        st.caption("voicebooking-speech.wav not found in clipped_samples/.")

    st.divider()
    st.subheader("Noise clips by category")

    category = st.selectbox("Category", options=categories, key="category_select")
    clips = get_clips_for_category(clip_rows, category)
    st.caption(f"{len(clips)} clips in {category}.")

    prev_sample = None
    sample_ix = 0
    ver = 0
    for idx, row in enumerate(clips):
        clip_id = row["clip_id"]
        path = row["path"]
        sample_key = f"{row['category']}/{row['filename']}"
        if sample_key != prev_sample:
            sample_ix += 1
            ver = 1
            prev_sample = sample_key
        else:
            ver += 1

        if not path.exists():
            st.warning(f"Missing: {path}")
            continue

        st.markdown(f"**Sample {sample_ix}, ver {ver}**")
        play_mode = st.radio(
            "Play",
            options=["Noise only", "Mixed (noise + clean speech)"],
            key=f"mode_{clip_id}",
            horizontal=True,
        )

        if play_mode == "Noise only":
            st.audio(noise_to_wav_bytes(path, row["level_db"]), format="audio/wav")
        else:
            if CLEAN_AUDIO_PATH.exists():
                mixed_bytes, _ = mix_clean_and_noise(CLEAN_AUDIO_PATH, path, row["level_db"])
                st.audio(mixed_bytes, format="audio/wav")
            else:
                st.warning("Clean speech file missing; cannot play mixed.")

        current = st.session_state["votes"].get(clip_id, "medium")
        choice = st.selectbox(
            "Perceived level",
            options=LABELS,
            index=LABELS.index(current) if current in LABELS else 2,
            key=clip_id,
            label_visibility="collapsed",
        )
        st.session_state["votes"][clip_id] = choice
        st.markdown("---")

    st.divider()
    st.subheader("Submit or export")
    all_clip_ids = {r["clip_id"] for r in clip_rows}
    if st.session_state["votes"]:
        col_submit, col_dl = st.columns(2)
        with col_submit:
            if st.button("Submit my responses"):
                respondent_id = str(uuid.uuid4())
                if append_responses_to_file(respondent_id, st.session_state["votes"], clip_rows):
                    st.success("Thanks, your responses have been saved.")
                else:
                    st.warning("No votes to save.")
        with col_dl:
            from datetime import datetime
            clip_lookup = {r["clip_id"]: r for r in clip_rows}
            output = io.StringIO()
            w = csv.writer(output)
            w.writerow(["clip_id", "label", "category", "level_db", "snr_db"])
            for cid, label in st.session_state["votes"].items():
                if cid in all_clip_ids and cid in clip_lookup:
                    r = clip_lookup[cid]
                    snr_db = CLEAN_SPEECH_LEVEL_DB - r["level_db"]
                    w.writerow([cid, label, r["category"], r["level_db"], round(snr_db, 1)])
            csv_str = output.getvalue()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "Download my responses (CSV)",
                data=csv_str,
                file_name=f"survey_responses_{ts}.csv",
                mime="text/csv",
            )
    else:
        st.info("Select perceived level for at least one clip above.")


if __name__ == "__main__":
    main()

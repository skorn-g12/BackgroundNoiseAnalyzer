# BackgroundNoise Intensity Experiment

Produce background noise clips at known RMS levels (-40 dB to -10 dB in 5 dB steps) so a wider audience can label perceived level (very_low / low / medium / high / very_high). Results are used to map these five labels to dB for a voice simulator.

**Quick reference:** See [STEPS.md](STEPS.md) for the ordered sequence and for **what to run after updating raw files** (process_originals → generate_levels → build_survey_bundle).

## Setup

```bash
cd shivani/BackgroundNoise
pip install -r requirements.txt
```

## Workflow

### 1. Get samples (choose one)

- **Option A – Freesound API**  
  Get a free API key at [Freesound API](https://freesound.org/apiv2/apply/). Then:
  ```bash
  export FREESOUND_API_KEY=your_key
  # or add FREESOUND_API_KEY=your_key to .env in this directory
  python download_samples.py
  ```
  This downloads up to 5 sounds per category into `raw/<Category>/` (preferring duration ≤ 10 s). Attribution is written to `attribution.json`; please credit Freesound and authors per license.

- **Option B – URL manifest**  
  Maintain a `sources.yaml` (or similar) with 5 URLs per category and a small script to download into `raw/Office/`, `raw/Cafe/`, etc.

- **Option C – Manual**  
  Download 5 WAV/MP3 files per category from Freesound (or other CC sources) and place them in `raw/Office/`, `raw/Cafe/`, `raw/StreetTraffic/`, `raw/Home/`, `raw/CallCenter/`, `raw/Construction/`, `raw/Airport/`.

### 2. Process originals

```bash
python process_originals.py
```

- Reads from `raw/<Category>/`, trims to max 10 s, resamples to 16 kHz, converts to mono.
- Computes original RMS dB and writes files to `Office/`, `Cafe/`, … as `office_01.wav`, etc.
- Writes `manifest_original.csv` (category, sample_id, filename, original_rms_db, duration_sec, path).

### 3. Generate level variants

```bash
python generate_levels.py
```

- For each original, generates 7 level-normalized WAVs at -40, -35, -30, -25, -20, -15, -10 dB.
- Saves as e.g. `Office/office_01_level_-40db.wav` … `Office/office_01_level_-10db.wav`.

### 4. Build survey bundle (anonymized clips)

```bash
python build_survey_bundle.py
```

- Copies selected level-normalized clips into `levels/` with anonymized names: `clip_0001.wav`, `clip_0002.wav`, …
- Writes `survey_mapping.csv` with columns `clip_id`, `category`, `sample_id`, `level_db`.
- **Keep `survey_mapping.csv` private**; do not share with participants so they are not influenced by filenames.

### 5. Run the survey (Streamlit app)

- Start the app and expose it (e.g. with ngrok):
  ```bash
  streamlit run survey_app.py --server.address 0.0.0.0
  # In another terminal: ngrok http 8501
  ```
- Share the ngrok URL. Respondents pick a category, play each clip, choose **very_low / low / medium / high / very_high**, then click **Submit my responses** (saved to `collected_responses.csv` on the server) or **Download my responses** to keep a copy.

### 6. Post-survey: map labels to the voice simulator (automated)

- If everyone used Submit, responses are in `collected_responses.csv`. To include any downloaded CSVs too: `python merge_responses.py collected_responses.csv survey_responses_*.csv -o merged_responses.csv`
- Aggregate and write mapping: `python aggregate_survey_responses.py collected_responses.csv -o level_mapping.json` (or use `merged_responses.csv` if you merged).
- Use `level_mapping.json` (label → median dB) in the voice simulator.

## Directory layout

- `raw/<Category>/` – Staging: downloaded or manually added files.
- `Office/`, `Cafe/`, … – Processed originals and level variants (`*_level_-40db.wav`, …).
- `levels/` – Survey bundle: anonymized clips only.
- `manifest_original.csv` – Original files and their RMS dB.
- `survey_mapping.csv` – Mapping from clip_id to category, sample_id, level_db (private).
- `collected_responses.csv` – Server-saved responses when respondents click Submit (optional; in .gitignore).

## Licensing and attribution

When using Freesound content, comply with each sound’s license and credit Freesound and the author. The download script writes `attribution.json` for this purpose.

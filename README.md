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

### 5. Run the survey

#### Option A: Local deployment (with ngrok)
- Start the app and expose it:
  ```bash
  streamlit run survey_app.py --server.address 0.0.0.0
  # In another terminal: ngrok http 8501
  ```
- Share the ngrok URL. Responses are saved to `collected_responses.csv` on your local machine.

#### Option B: Cloud deployment (Streamlit Cloud + Google Sheets) - **Recommended**
- Follow the setup guide in `GOOGLE_SHEETS_SETUP.md` to configure Google Sheets
- Deploy to Streamlit Cloud using `survey_app_cloud.py` as the main file
- Share the permanent Streamlit Cloud URL (e.g., `https://your-app.streamlit.app`)
- Responses are automatically saved to your Google Sheet

**Benefits of cloud deployment:**
- ✅ Permanent URL (no ngrok restarts)
- ✅ No SSL/protocol errors
- ✅ Responses persist in Google Sheets
- ✅ Can view responses in real-time
- ✅ Free hosting

### 6. Download responses from Google Sheets (if using cloud deployment)

If you deployed to Streamlit Cloud, download the responses from Google Sheets:

```bash
python download_responses_from_sheets.py \
  --credentials google_credentials.json \
  --sheet-url "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit" \
  --output collected_responses.csv
```

This downloads all responses into the same CSV format used by the local app.

### 7. Post-survey: map labels to the voice simulator (automated)

- Aggregate and compute median dB per label per category:
  ```bash
  python aggregate_survey_responses.py collected_responses.csv -o level_mapping.json
  ```
- This outputs:
  - Console: Detailed statistics (count, median, min, max per label per category)
  - `level_mapping.json`: Category → Label → Median dB mapping for the voice simulator
- Use `level_mapping.json` in your voice simulator (e.g., VOCSIM's `noise_personas.yaml`)

## Directory layout

- `raw/<Category>/` – Staging: downloaded or manually added files.
- `Office/`, `Cafe/`, … – Processed originals and level variants (`*_level_-40db.wav`, …).
- `levels/` – Survey bundle: anonymized clips only.
- `manifest_original.csv` – Original files and their RMS dB.
- `survey_mapping.csv` – Mapping from clip_id to category, sample_id, level_db (private).
- `collected_responses.csv` – Server-saved responses when respondents click Submit (optional; in .gitignore).

## Licensing and attribution

When using Freesound content, comply with each sound’s license and credit Freesound and the author. The download script writes `attribution.json` for this purpose.

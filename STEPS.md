# BackgroundNoise: Step-by-step sequence

## One-time setup

1. **Install dependencies**
   ```bash
   cd shivani/BackgroundNoise
   pip install -r requirements.txt
   ```

---

## Full pipeline (first time or after changing raw files)

2. **Get samples** (pick one)
   - **Option A:** Set `FREESOUND_API_KEY`, then run `python download_samples.py`
   - **Option B:** Use a URL manifest / script to download into `raw/<Category>/`
   - **Option C:** Manually put 5 files per category in `raw/Office/`, `raw/Cafe/`, `raw/StreetTraffic/`, `raw/Home/`, `raw/CallCenter/`, `raw/Construction/`, `raw/Airport/`

3. **Process originals**
   ```bash
   python process_originals.py
   ```
   (Reads `raw/`, trims to 10 s, 16 kHz mono, writes category dirs + `manifest_original.csv`.)

4. **Generate level variants**
   ```bash
   python generate_levels.py
   ```
   (Builds 7 levels per original: -40, -35, -30, -25, -20, -15, -10 dB.)

5. **Build survey bundle** (optional, for sharing anonymized clips)
   ```bash
   python build_survey_bundle.py
   ```
   (Fills `levels/` and writes `survey_mapping.csv`.)

6. **Run the survey app** (Streamlit + ngrok)
   ```bash
   streamlit run survey_app.py --server.address 0.0.0.0
   ```
   In another terminal, expose the app:
   ```bash
   ngrok http 8501
   ```
   Share the ngrok HTTPS URL. Respondents pick a category, play clips, choose very_low / low / medium / high / very_high per clip, then click **Submit my responses** (saved to `collected_responses.csv` on the server) or **Download my responses** to keep a local copy.

7. **Post-survey analysis** (automated)
   - If using the app’s Submit button, responses are in `collected_responses.csv`. To add downloaded CSVs as well, merge first:
     ```bash
     python merge_responses.py collected_responses.csv survey_responses_*.csv -o merged_responses.csv
     ```
   - Compute median dB per label and write the voice-simulator mapping:
     ```bash
     python aggregate_survey_responses.py collected_responses.csv -o level_mapping.json
     ```
     (Or use `merged_responses.csv` if you merged files.)
   Use `level_mapping.json` (or `level_mapping.csv`) in the voice simulator as label → dB.

---

## After updating raw files

If you add, remove, or replace files in `raw/<Category>/`:

1. **Process originals again**
   ```bash
   python process_originals.py
   ```
   This overwrites/updates the category dirs and `manifest_original.csv`.

2. **Regenerate level variants**
   ```bash
   python generate_levels.py
   ```
   This overwrites the `*_level_*db.wav` files based on the current manifest and originals.

3. **Rebuild survey bundle** (if you use it)
   ```bash
   python build_survey_bundle.py
   ```
   This refreshes `levels/` and `survey_mapping.csv` from the new level files.

You do **not** need to re-download unless you want different source files; re-running from step 3 (process_originals) is enough after any change under `raw/`.

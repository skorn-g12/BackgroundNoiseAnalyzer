"""
Streamlit survey app with Google Sheets integration for cloud deployment.
Responses are stored in a Google Sheet instead of local CSV.
"""
import csv
import io
import uuid
from pathlib import Path
from datetime import datetime

import streamlit as st

from config import CATEGORIES, LEVELS_DIR, SURVEY_MAPPING_CSV

LABELS = ["very_low", "low", "medium", "high", "very_high"]


def load_mapping():
    """Return list of dicts with clip_id, category, sample_id, level_db."""
    rows = []
    with open(SURVEY_MAPPING_CSV, newline="") as f:
        for row in csv.DictReader(f):
            row["level_db"] = int(row["level_db"])
            rows.append(row)
    return rows


def get_categories_in_mapping(mapping_rows):
    """Unique categories present in mapping, in CATEGORIES order."""
    present = {r["category"] for r in mapping_rows}
    return [c for c in CATEGORIES if c in present]


def get_clips_for_category(mapping_rows, category):
    """Rows for category, sorted by sample_id then level_db."""
    subset = [r for r in mapping_rows if r["category"] == category]
    return sorted(subset, key=lambda r: (r["sample_id"], r["level_db"]))


def save_to_google_sheets(respondent_id: str, votes: dict, mapping: list) -> bool:
    """Save responses to Google Sheets using Streamlit secrets."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Get credentials from Streamlit secrets
        credentials_dict = st.secrets["gcp_service_account"]
        
        # Define the scope
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        # Authorize and open the sheet
        client = gspread.authorize(credentials)
        sheet_url = st.secrets["google_sheets"]["sheet_url"]
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.sheet1  # Use first sheet
        
        # Prepare rows to append
        clip_to_row = {r["clip_id"]: r for r in mapping}
        rows_to_add = []
        
        for cid, label in votes.items():
            if cid not in clip_to_row:
                continue
            row_data = clip_to_row[cid]
            rows_to_add.append([
                respondent_id,
                cid,
                label,
                row_data["category"],
                row_data["sample_id"],
                row_data["level_db"],
                datetime.now().isoformat()
            ])
        
        if not rows_to_add:
            return False
        
        # Check if sheet is empty and add header if needed
        existing_data = worksheet.get_all_values()
        if not existing_data:
            worksheet.append_row([
                "respondent_id", "clip_id", "label", "category", 
                "sample_id", "level_db", "timestamp"
            ])
        
        # Append all rows at once
        worksheet.append_rows(rows_to_add)
        return True
        
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")
        return False


def main():
    st.set_page_config(page_title="Background noise level survey", layout="wide")
    st.title("Background noise level survey")
    st.markdown("Pick a category, listen to each clip, and choose the perceived loudness (very_low → very_high).")

    if "votes" not in st.session_state:
        st.session_state["votes"] = {}

    mapping = load_mapping()
    categories_available = get_categories_in_mapping(mapping)
    if not categories_available:
        st.error("No categories found in survey_mapping.csv.")
        return

    category = st.selectbox(
        "Category",
        options=categories_available,
        key="category_select",
    )
    clips = get_clips_for_category(mapping, category)
    st.caption(f"{len(clips)} clips in this category.")

    prev_sample = None
    ver = 0
    for row in clips:
        clip_id = row["clip_id"]
        sample_id = row["sample_id"]
        level_db = row["level_db"]
        if row["sample_id"] != prev_sample:
            ver = 1
            prev_sample = row["sample_id"]
        else:
            ver += 1
        audio_path = LEVELS_DIR / f"{clip_id}.wav"

        if not audio_path.exists():
            st.warning(f"Missing audio: {clip_id}")
            continue

        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.markdown(f"**Sample {sample_id}, ver {ver}**")
            st.audio(str(audio_path))
        with col2:
            st.write("")
        with col3:
            current = st.session_state["votes"].get(clip_id, "medium")
            choice = st.selectbox(
                "Perceived level",
                options=LABELS,
                index=LABELS.index(current) if current in LABELS else 2,
                key=clip_id,
                label_visibility="collapsed",
            )
            st.session_state["votes"][clip_id] = choice

    st.divider()
    st.subheader("Submit or export")
    if st.session_state["votes"]:
        col_submit, col_dl = st.columns(2)
        with col_submit:
            if st.button("Submit my responses"):
                respondent_id = str(uuid.uuid4())
                if save_to_google_sheets(respondent_id, st.session_state["votes"], mapping):
                    st.success("Thanks, your responses have been saved to Google Sheets!")
                    st.balloons()
                else:
                    st.warning("Failed to save responses. Please try downloading instead.")
        with col_dl:
            output = io.StringIO()
            w = csv.writer(output)
            w.writerow(["clip_id", "label", "category", "level_db"])
            for row in mapping:
                cid = row["clip_id"]
                if cid in st.session_state["votes"]:
                    w.writerow([
                        cid,
                        st.session_state["votes"][cid],
                        row["category"],
                        row["level_db"],
                    ])
            csv_str = output.getvalue()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "Download my responses (CSV)",
                data=csv_str,
                file_name=f"survey_responses_{ts}.csv",
                mime="text/csv",
            )
    else:
        st.info("Select perceived level for at least one clip above, then submit or download your responses here.")


if __name__ == "__main__":
    main()

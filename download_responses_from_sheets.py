"""
Download survey responses from Google Sheets to a local CSV file.
This allows you to run the aggregate_survey_responses.py script on cloud-collected data.

Usage:
    python download_responses_from_sheets.py --output collected_responses.csv
"""
import argparse
import csv
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


def download_responses(credentials_json: Path, sheet_url: str, output_path: Path) -> None:
    """Download all responses from Google Sheets to a CSV file."""
    
    # Define the scope
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    # Create credentials
    credentials = Credentials.from_service_account_file(
        str(credentials_json),
        scopes=scopes
    )
    
    # Authorize and open the sheet
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(sheet_url)
    worksheet = spreadsheet.sheet1
    
    # Get all data
    all_data = worksheet.get_all_records()
    
    if not all_data:
        print("No data found in the sheet.")
        return
    
    # Write to CSV in the format expected by aggregate_survey_responses.py
    # Required columns: respondent_id, clip_id, label
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["respondent_id", "clip_id", "label"])
        writer.writeheader()
        
        for row in all_data:
            writer.writerow({
                "respondent_id": row.get("respondent_id", ""),
                "clip_id": row.get("clip_id", ""),
                "label": row.get("label", "")
            })
    
    print(f"Downloaded {len(all_data)} responses to {output_path}")
    print(f"\nYou can now run:")
    print(f"python aggregate_survey_responses.py {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Download survey responses from Google Sheets to CSV"
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("google_credentials.json"),
        help="Path to Google service account JSON credentials file"
    )
    parser.add_argument(
        "--sheet-url",
        type=str,
        required=True,
        help="URL of the Google Sheet containing responses"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("collected_responses.csv"),
        help="Output CSV file path (default: collected_responses.csv)"
    )
    
    args = parser.parse_args()
    
    if not args.credentials.exists():
        print(f"Error: Credentials file not found: {args.credentials}")
        print("\nPlease download your service account JSON key from Google Cloud Console")
        print("and save it as 'google_credentials.json' (or specify path with --credentials)")
        return
    
    try:
        download_responses(args.credentials, args.sheet_url, args.output)
    except Exception as e:
        print(f"Error downloading responses: {e}")
        print("\nMake sure:")
        print("1. The sheet URL is correct")
        print("2. The service account has access to the sheet")
        print("3. Google Sheets API is enabled in your Google Cloud project")


if __name__ == "__main__":
    main()

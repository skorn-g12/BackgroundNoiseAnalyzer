# Google Sheets Setup for Survey Responses

This guide explains how to set up Google Sheets to collect survey responses when deployed to Streamlit Cloud.

## Step 1: Create a Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it "Background Noise Survey Responses" (or any name you prefer)
4. Copy the URL of the sheet (you'll need this later)

## Step 2: Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Enable the Google Drive API (same process as above)
5. Create a service account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Give it a name like "streamlit-survey-app"
   - Click "Create and Continue"
   - Skip the optional steps and click "Done"
6. Create a JSON key:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Download the JSON file (keep it safe!)

## Step 3: Share the Google Sheet with the Service Account

1. Open the JSON key file you downloaded
2. Find the `client_email` field (looks like: `your-service-account@project-id.iam.gserviceaccount.com`)
3. Go back to your Google Sheet
4. Click "Share" button
5. Paste the service account email
6. Give it "Editor" permissions
7. Click "Send" (uncheck "Notify people" since it's a service account)

## Step 4: Configure Streamlit Cloud Secrets

When deploying to Streamlit Cloud:

1. Go to your app settings in Streamlit Cloud
2. Click on "Secrets" in the left sidebar
3. Add the following secrets in TOML format:

```toml
# Google Sheets configuration
[google_sheets]
sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

# Google Cloud Service Account credentials
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project-id.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40project-id.iam.gserviceaccount.com"
```

**Important:** Copy all the values from your downloaded JSON key file into the secrets configuration.

## Step 5: Deploy to Streamlit Cloud

1. Commit and push your changes to GitHub
2. Deploy using `survey_app_cloud.py` as the main file
3. The app will automatically use the secrets to save responses to your Google Sheet

## Data Structure

The Google Sheet will have the following columns:
- `respondent_id`: Unique ID for each survey submission
- `clip_id`: ID of the audio clip
- `label`: User's perceived level (very_low, low, medium, high, very_high)
- `category`: Noise category (Office, Cafe, etc.)
- `sample_id`: Sample identifier
- `level_db`: Actual dB level of the clip
- `timestamp`: When the response was submitted

## Viewing Responses

Simply open your Google Sheet to view all collected responses. You can:
- Download as CSV for analysis
- Create charts and visualizations
- Share with team members
- Use Google Sheets formulas for basic analysis

## Troubleshooting

**Error: "Permission denied"**
- Make sure you shared the sheet with the service account email
- Verify the service account has "Editor" permissions

**Error: "API not enabled"**
- Enable both Google Sheets API and Google Drive API in Google Cloud Console

**Error: "Invalid credentials"**
- Double-check that all fields from the JSON key are correctly copied to Streamlit secrets
- Make sure the private_key includes the full key with `\n` newlines preserved

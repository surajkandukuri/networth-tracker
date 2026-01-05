# networth-tracker (Quarterly Net Worth Email)

This repo runs a **fully automated quarterly job** that:
1) Fetches **free CAD/parcel market values** for:
   - Primary Home (Collin CAD via ArcGIS)
   - Celina land (Collin CAD via ArcGIS point query)
   - Cedar Hill commercial (Dallas County parcels via ArcGIS)
2) Generates the **frozen Email #2 format** (structure unchanged).
3) Generates the **simple line chart** (no legend, no clutter, end-of-line labels only).
4) Sends the email via **Gmail API OAuth (Option B)** (NO Gmail password).
5) Stores `snapshots/latest.json` + timestamped snapshots for audit/history.

## 0) Uploading the repo
You can upload via GitHub UI:
- Unzip the download
- Repo → **uploading an existing file**
- Drag all files/folders (not the zip) → Commit

## 1) Gmail OAuth setup (Option B)
### 1.1 Create OAuth Client in Google Cloud
- Create a Google Cloud Project
- Enable **Gmail API**
- Create OAuth Client ID → **Desktop app**
- Download the `client_secret.json`

### 1.2 Generate Refresh Token (one time, on your laptop)
```bash
pip install -r tools/requirements-dev.txt
python tools/get_refresh_token.py --client-secrets /path/to/client_secret.json
```

### 1.3 Add GitHub Secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `EMAIL_TO` (where you want to receive the email; can be the same Gmail)

## 2) Run
- Manual: Actions → Quarterly Net Worth Tracker → Run workflow
- Scheduled: runs quarterly (Jan/Apr/Jul/Oct 1st)

## Notes
- This repo injects the fetched **real estate values** into Table 1.
- Securities APIs can be wired next **without changing the email format**.
- If you want to test without sending email:
  - set `run.dry_run: true` in `config.yaml`
  - or set GitHub Actions env `DRY_RUN=1`

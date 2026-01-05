"""One-time helper to generate a Gmail OAuth refresh token (Option B).

Run locally (NOT in GitHub Actions):
  1) pip install -r tools/requirements-dev.txt
  2) Download OAuth client JSON from Google Cloud Console (Desktop app).
  3) python tools/get_refresh_token.py --client-secrets path/to/client_secret.json

It will open a browser, you approve once, and it prints the refresh token.
"""

from __future__ import annotations

import argparse

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-secrets", required=True, help="Path to OAuth client_secret.json")
    args = ap.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    print("\n=== COPY THIS INTO GITHUB SECRET: GOOGLE_REFRESH_TOKEN ===")
    print(creds.refresh_token)
    print("==========================================================\n")


if __name__ == "__main__":
    main()

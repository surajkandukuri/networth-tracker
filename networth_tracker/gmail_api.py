from __future__ import annotations

import base64
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Optional

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class GmailOAuthError(RuntimeError):
    pass


def get_access_token() -> str:
    """Exchange refresh token for an access token.

    Requires env vars:
      - GOOGLE_CLIENT_ID
      - GOOGLE_CLIENT_SECRET
      - GOOGLE_REFRESH_TOKEN
    """
    cid = os.environ.get("GOOGLE_CLIENT_ID")
    csec = os.environ.get("GOOGLE_CLIENT_SECRET")
    rt = os.environ.get("GOOGLE_REFRESH_TOKEN")

    if not cid or not csec or not rt:
        raise GmailOAuthError("Missing GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN env vars.")

    payload = {
        "client_id": cid,
        "client_secret": csec,
        "refresh_token": rt,
        "grant_type": "refresh_token",
    }
    r = requests.post(TOKEN_URL, data=payload, timeout=30)
    if r.status_code != 200:
        raise GmailOAuthError(f"Token exchange failed: {r.status_code} {r.text}")
    data = r.json()
    token = data.get("access_token")
    if not token:
        raise GmailOAuthError(f"No access_token in response: {data}")
    return token


def send_email_html_with_inline_image(
    subject: str,
    sender: str,
    to: str,
    html_body: str,
    inline_png_path: Optional[str] = None,
    inline_cid: str = "chart",
) -> dict:
    """Send an HTML email via Gmail API with optional inline image."""
    msg_root = MIMEMultipart("related")
    msg_root["Subject"] = subject
    msg_root["From"] = sender
    msg_root["To"] = to

    msg_alt = MIMEMultipart("alternative")
    msg_root.attach(msg_alt)

    msg_alt.attach(MIMEText(html_body, "html", "utf-8"))

    if inline_png_path:
        with open(inline_png_path, "rb") as f:
            img = MIMEImage(f.read(), _subtype="png")
        img.add_header("Content-ID", f"<{inline_cid}>")
        img.add_header("Content-Disposition", "inline", filename="chart.png")
        msg_root.attach(img)

    raw_bytes = msg_root.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"raw": raw_b64}

    r = requests.post(GMAIL_SEND_URL, headers=headers, data=json.dumps(body), timeout=30)
    if r.status_code not in (200, 202):
        raise GmailOAuthError(f"Gmail send failed: {r.status_code} {r.text}")
    return r.json()

"""Transactional email via Resend HTTP API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings


class EmailNotConfiguredError(RuntimeError):
    pass


def resend_configured() -> bool:
    return bool(get_settings().resend_api_key.strip())


def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
) -> Dict[str, Any]:
    settings = get_settings()
    api_key = settings.resend_api_key.strip()
    if not api_key:
        raise EmailNotConfiguredError(
            "RESEND_API_KEY is not set. Add it on Railway to send weekly digests."
        )

    payload = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Resend error {response.status_code}: {response.text[:400]}"
        )
    try:
        return response.json()
    except ValueError:
        return {"ok": True}


def render_digest_email(
    *,
    listings: List[Dict[str, Any]],
    unsubscribe_url: str,
    discord_url: str,
) -> tuple[str, str, str]:
    """Return (subject, html, text) for a Friday digest."""
    count = len(listings)
    subject = f"Your Friday shortlist · {count} hackathon{'s' if count != 1 else ''}"

    rows_html: List[str] = []
    rows_text: List[str] = []
    for item in listings:
        title = item.get("title") or "Untitled"
        url = item.get("url") or "#"
        organizer = item.get("organizer") or ""
        prize = item.get("prize_pool_usd")
        deadline = item.get("deadline_label") or "deadline TBA"
        reason = item.get("fit_reason") or ""
        prize_bit = f"${prize:,}" if isinstance(prize, int) and prize > 0 else "no cash prize"
        rows_html.append(
            "<tr>"
            f'<td style="padding:12px 0;border-bottom:1px solid #ddd;">'
            f'<a href="{url}" style="color:#0000cc;font-weight:bold;">{_escape(title)}</a><br/>'
            f'<span style="color:#666;">{_escape(organizer)} · {prize_bit} · {_escape(deadline)}</span>'
            + (
                f'<br/><span style="color:#333;">{_escape(reason)}</span>'
                if reason
                else ""
            )
            + "</td></tr>"
        )
        rows_text.append(
            f"- {title}\n  {url}\n  {organizer} · {prize_bit} · {deadline}"
            + (f"\n  {reason}" if reason else "")
        )

    html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#000;max-width:560px;margin:0 auto;padding:24px;">
  <p style="margin:0 0 4px;color:#7b0099;font-weight:bold;">FindHackathons</p>
  <h1 style="font-size:20px;margin:0 0 8px;">Friday shortlist</h1>
  <p style="color:#333;margin:0 0 20px;">
    {count} competition{'s' if count != 1 else ''} matching your level, closing soon.
  </p>
  <table style="width:100%;border-collapse:collapse;">{''.join(rows_html)}</table>
  <p style="margin:24px 0 8px;color:#333;">
    Looking for teammates?
    <a href="{discord_url}" style="color:#0000cc;">Say hi on Discord</a>
  </p>
  <p style="margin:24px 0 0;font-size:12px;color:#666;">
    <a href="{unsubscribe_url}" style="color:#666;">Unsubscribe</a>
    · One email a week · No spam
  </p>
</body></html>"""

    text = (
        "FindHackathons — Friday shortlist\n\n"
        + "\n\n".join(rows_text)
        + f"\n\nLooking for teammates? {discord_url}\n"
        + f"\nUnsubscribe: {unsubscribe_url}\n"
    )
    return subject, html, text


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

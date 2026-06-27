"""Smartlead API service for email campaign sending and analytics."""
import aiohttp
from config.settings import get_settings


class SmartleadService:
    """Send emails and track campaign performance via Smartlead."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.smartlead_api_key
        self.base_url = "https://api.smartlead.ai/v1"

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an authenticated request to Smartlead API."""
        if not self.api_key:
            return {"error": "Smartlead API key not configured"}
        url = f"{self.base_url}{endpoint}"
        params = kwargs.get("params", {})
        params["api_key"] = self.api_key
        kwargs["params"] = params

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                return {"error": f"HTTP {resp.status}", "detail": await resp.text()}

    async def send_email(self, to_email: str, subject: str, body: str, campaign_id: str = None, from_email: str = None) -> dict:
        """Send a single email via Smartlead."""
        payload = {
            "email": to_email,
            "subject": subject,
            "body": body,
        }
        if campaign_id:
            payload["campaign_id"] = campaign_id
        if from_email:
            payload["from_email"] = from_email
        return await self._request("POST", "/campaigns/send-test-email", json=payload)

    async def create_lead(self, campaign_id: str, email: str, first_name: str = "", last_name: str = "", company: str = "", custom_fields: dict = None) -> dict:
        """Add a lead to a Smartlead campaign."""
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company_name": company,
        }
        if custom_fields:
            payload.update(custom_fields)
        return await self._request("POST", f"/campaigns/{campaign_id}/leads", json=payload)

    async def get_campaign_stats(self, campaign_id: str) -> dict:
        """Get analytics for a campaign."""
        return await self._request("GET", f"/campaigns/{campaign_id}/analytics")

    async def get_campaigns(self) -> dict:
        """List all campaigns."""
        return await self._request("GET", "/campaigns")

    async def get_email_sequence(self, campaign_id: str) -> dict:
        """Get email sequence for a campaign."""
        return await self._request("GET", f"/campaigns/{campaign_id}/email-sequence")

    async def update_campaign_schedule(self, campaign_id: str, schedule: dict) -> dict:
        """Update campaign sending schedule."""
        return await self._request("POST", f"/campaigns/{campaign_id}/schedule", json=schedule)

    async def webhook_handler(self, payload: dict) -> dict:
        """Process incoming Smartlead webhook events (open, click, reply, bounce)."""
        event_type = payload.get("event", "")
        email = payload.get("email", "")
        message_id = payload.get("message_id", "")

        return {
            "event": event_type,
            "email": email,
            "message_id": message_id,
            "processed": True,
        }

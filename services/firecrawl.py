"""Firecrawl API service for website scraping and research."""
import aiohttp
from config.settings import get_settings


class FirecrawlService:
    """Scrape and extract data from business websites."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.firecrawl_api_key
        self.base_url = "https://api.firecrawl.dev/v1"

    async def scrape(self, url: str) -> dict:
        """Scrape a single URL and return markdown + links."""
        if not self.api_key:
            return {"error": "Firecrawl API key not configured"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/scrape",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"url": url, "formats": ["markdown", "links", "html"]}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}", "detail": await resp.text()}

    async def crawl(self, url: str, limit: int = 10) -> dict:
        """Crawl a website up to `limit` pages."""
        if not self.api_key:
            return {"error": "Firecrawl API key not configured"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/crawl",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "url": url,
                    "limit": limit,
                    "scrapeOptions": {"formats": ["markdown", "links"]}
                }
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}", "detail": await resp.text()}

    async def map(self, url: str) -> dict:
        """Map all URLs on a website."""
        if not self.api_key:
            return {"error": "Firecrawl API key not configured"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/map",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"url": url}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}", "detail": await resp.text()}

    async def extract_business_info(self, url: str) -> dict:
        """Extract structured business info from a website."""
        scrape_result = await self.scrape(url)
        if "error" in scrape_result:
            return scrape_result

        data = scrape_result.get("data", {})
        markdown = data.get("markdown", "")
        links = data.get("links", [])
        html = data.get("html", "")

        # Detect common chat/live chat tools
        chat_tools = []
        chat_patterns = [
            "intercom", "drift", "zendesk", "crisp", "tawk.to", "tidio",
            "livechat", "chatbot", "olark", "purechat", "snapengage",
            "hubspot", "chatra", "gorgias", "helpcrunch", "chatwoot",
            "ada", "forethought", "kustomer", "gladly", "zoho desk"
        ]
        html_lower = html.lower() if html else ""
        for tool in chat_patterns:
            if tool.lower() in html_lower:
                chat_tools.append(tool)

        # Detect contact channels
        has_contact_form = "contact" in html_lower or any("contact" in l.lower() for l in links)
        has_whatsapp = "whatsapp" in html_lower
        has_facebook = "facebook.com" in html_lower or any("facebook.com" in l for l in links)
        has_instagram = "instagram.com" in html_lower or any("instagram.com" in l for l in links)
        has_blog = "/blog" in html_lower or any("blog" in l.lower() for l in links)
        has_faq = "faq" in html_lower or any("faq" in l.lower() for l in links)
        has_about = "about" in html_lower or any("about" in l.lower() for l in links)
        has_services = "service" in html_lower or any("service" in l.lower() for l in links)

        # Extract email with simple regex
        import re
        emails = re.findall(r'[\w.-]+@[\w.-]+\.[\w]{2,}', html)
        has_contact_email = len(emails) > 0

        return {
            "website_live": True,
            "has_contact_email": has_contact_email,
            "has_contact_form": has_contact_form,
            "has_whatsapp": has_whatsapp,
            "has_facebook": has_facebook,
            "has_instagram": has_instagram,
            "has_blog": has_blog,
            "has_faq": has_faq,
            "has_about": has_about,
            "has_services": has_services,
            "website_summary": markdown[:3000] if markdown else "",
            "chat_tools": list(set(chat_tools)),
            "has_live_chat": len(chat_tools) > 0 and any(t in ["intercom", "drift", "tawk.to", "tidio", "livechat", "olark"] for t in chat_tools),
            "has_ai_chat": len(chat_tools) > 0 and any(t in ["ada", "forethought", "intercom", "drift", "chatbot"] for t in chat_tools),
            "emails_found": list(set(emails))[:5],
        }

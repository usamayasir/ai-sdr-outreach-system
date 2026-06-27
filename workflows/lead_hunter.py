"""Lead Hunter: Discover local business leads via Google Places API + web scraping."""
import aiohttp
import asyncio
from typing import List, Dict
from config.settings import get_settings


class LeadHunter:
    """Hunt for leads using Google Places API and Apollo.io (optional)."""

    def __init__(self):
        self.settings = get_settings()
        self.google_maps_key = self.settings.google_maps_api_key
        self.apollo_key = self.settings.apollo_api_key

    # ── Google Places ────────────────────────────────────────

    async def search_places(self, query: str, location: str = None, radius: int = 50000) -> List[Dict]:
        """Search Google Places for businesses."""
        if not self.google_maps_key:
            return []

        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": self.google_maps_key,
            "radius": radius,
        }
        if location:
            params["location"] = location

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                return data.get("results", [])

    async def get_place_details(self, place_id: str) -> Dict:
        """Get detailed info for a place."""
        if not self.google_maps_key:
            return {}

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,website,formatted_phone_number,formatted_address,rating,user_ratings_total,types,url",
            "key": self.google_maps_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                return data.get("result", {})

    async def hunt(self, industry: str, country: str, city: str, target: int) -> List[Dict]:
        """Main hunt method: find leads matching criteria."""
        query = f"{industry} in {city}, {country}"
        print(f"[LeadHunter] Searching: {query}")

        raw_results = await self.search_places(query)

        leads = []
        for result in raw_results[:target]:
            place_id = result.get("place_id")
            if not place_id:
                continue

            details = await self.get_place_details(place_id)
            await asyncio.sleep(0.2)  # Rate limit friendly

            lead = {
                "company": details.get("name") or result.get("name"),
                "website": details.get("website", ""),
                "phone": details.get("formatted_phone_number", ""),
                "address": details.get("formatted_address", ""),
                "google_rating": str(details.get("rating", "")),
                "reviews": details.get("user_ratings_total", 0),
                "category": ", ".join(details.get("types", [])) if details.get("types") else industry,
                "google_url": details.get("url", ""),
            }
            leads.append(lead)

        print(f"[LeadHunter] Found {len(leads)} leads")
        return leads

    # ── Apollo.io (optional enrichment) ──────────────────────

    async def enrich_with_apollo(self, company_name: str) -> Dict:
        """Enrich lead data with Apollo.io."""
        if not self.apollo_key:
            return {}

        url = "https://api.apollo.io/v1/organizations/enrich"
        headers = {"Authorization": f"Bearer {self.apollo_key}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"name": company_name}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    org = data.get("organization", {})
                    return {
                        "email": org.get("email", ""),
                        "linkedin": org.get("linkedin_url", ""),
                        "facebook": org.get("facebook_url", ""),
                        "phone": org.get("phone", ""),
                    }
                return {}

    async def enrich_leads(self, leads: List[Dict]) -> List[Dict]:
        """Batch enrich leads with Apollo data."""
        if not self.apollo_key:
            return leads

        for lead in leads:
            enrichment = await self.enrich_with_apollo(lead["company"])
            lead.update(enrichment)
            await asyncio.sleep(0.1)
        return leads

    # ── CSV Import (manual fallback) ─────────────────────────

    @staticmethod
    def from_csv(csv_path: str) -> List[Dict]:
        """Import leads from CSV file."""
        import csv
        leads = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(row)
        return leads

    # ── Save to Database ─────────────────────────────────────

    async def save_to_db(self, campaign_id: int, leads: List[Dict]) -> int:
        """Save hunted leads to the database."""
        from database.connection import async_session
        from database.models import Lead

        count = 0
        async with async_session() as session:
            for lead_data in leads:
                lead = Lead(
                    campaign_id=campaign_id,
                    company=lead_data.get("company"),
                    website=lead_data.get("website"),
                    phone=lead_data.get("phone"),
                    email=lead_data.get("email"),
                    facebook=lead_data.get("facebook"),
                    linkedin=lead_data.get("linkedin"),
                    address=lead_data.get("address"),
                    google_rating=lead_data.get("google_rating"),
                    reviews=lead_data.get("reviews"),
                    category=lead_data.get("category"),
                )
                session.add(lead)
                count += 1
            await session.commit()
        print(f"[LeadHunter] Saved {count} leads to database")
        return count

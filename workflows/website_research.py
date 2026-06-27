"""Website Research: Scrape and analyze lead websites using Firecrawl."""
from typing import Optional
from services.firecrawl import FirecrawlService
from database.connection import async_session
from database.models import Lead, LeadResearch, LeadStatus


class WebsiteResearch:
    """Research lead websites to extract business intelligence."""

    def __init__(self):
        self.firecrawl = FirecrawlService()

    async def process_lead(self, lead_id: int) -> Optional[LeadResearch]:
        """Research a single lead's website."""
        async with async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if not lead or not lead.website:
                return None

            print(f"[WebsiteResearch] Researching: {lead.company} — {lead.website}")
            info = await self.firecrawl.extract_business_info(lead.website)

            if "error" in info:
                print(f"[WebsiteResearch] Error for {lead.company}: {info['error']}")
                return None

            # Create or update research record
            research_result = await session.execute(
                select(LeadResearch).where(LeadResearch.lead_id == lead_id)
            )
            research = research_result.scalar_one_or_none()

            if not research:
                research = LeadResearch(lead_id=lead_id)
                session.add(research)

            research.website_live = info.get("website_live", False)
            research.has_contact_email = info.get("has_contact_email", False)
            research.has_contact_form = info.get("has_contact_form", False)
            research.has_whatsapp = info.get("has_whatsapp", False)
            research.has_facebook = info.get("has_facebook", False)
            research.has_instagram = info.get("has_instagram", False)
            research.has_blog = info.get("has_blog", False)
            research.has_faq = info.get("has_faq", False)
            research.has_about = info.get("has_about", False)
            research.has_services = info.get("has_services", False)
            research.website_summary = info.get("website_summary", "")
            research.chat_tools = info.get("chat_tools", [])
            research.has_live_chat = info.get("has_live_chat", False)
            research.has_ai_chat = info.get("has_ai_chat", False)

            # Update lead email if we found one
            if not lead.email and info.get("emails_found"):
                lead.email = info["emails_found"][0]

            lead.status = LeadStatus.RESEARCHED
            await session.commit()
            await session.refresh(research)
            print(f"[WebsiteResearch] Completed: {lead.company}")
            return research

    async def process_campaign(self, campaign_id: int, batch_size: int = 10) -> int:
        """Research all unresearched leads in a campaign."""
        from sqlalchemy import select, and_

        count = 0
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.campaign_id == campaign_id,
                        Lead.status == LeadStatus.NEW
                    )
                ).limit(batch_size)
            )
            leads = result.scalars().all()

        for lead in leads:
            await self.process_lead(lead.id)
            count += 1

        print(f"[WebsiteResearch] Processed {count} leads for campaign {campaign_id}")
        return count

    async def get_unresearched_leads(self, campaign_id: int, limit: int = 50) -> list:
        """Get leads that need website research."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.campaign_id == campaign_id,
                        Lead.status == LeadStatus.NEW,
                        Lead.website.isnot(None)
                    )
                ).limit(limit)
            )
            return result.scalars().all()

"""AI Qualification: Determine if a lead is worth pursuing using AI analysis."""
from database.connection import async_session
from database.models import Lead, LeadResearch, LeadStatus, CRMStatus
from services.ai_service import AIService


class AIQualification:
    """Qualify leads using AI to check for existing AI chat solutions and score fit."""

    def __init__(self):
        self.ai = AIService()

    async def qualify_lead(self, lead_id: int) -> bool:
        """Qualify a single lead and update database."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            if not lead:
                return False

            research_result = await session.execute(
                select(LeadResearch).where(LeadResearch.lead_id == lead_id)
            )
            research = research_result.scalar_one_or_none()
            if not research:
                print(f"[AIQualification] No research for lead {lead_id}")
                return False

            print(f"[AIQualification] Qualifying: {lead.company}")

            ai_result = await self.ai.qualify_website(
                website_summary=research.website_summary or "",
                chat_tools_found=research.chat_tools or []
            )

            research.qualified = ai_result.get("qualified", False)
            research.qualification_reason = ai_result.get("reason", "")
            research.has_live_chat = ai_result.get("has_live_chat", False)
            research.has_ai_chat = ai_result.get("has_ai_chat", False)
            research.chat_tools = ai_result.get("chat_tools", [])

            lead.ai_score = ai_result.get("ai_score", 0.0)

            if research.qualified and lead.ai_score >= 40.0:
                lead.status = LeadStatus.QUALIFIED
                if lead.crm_status == CRMStatus.LEAD:
                    lead.crm_status = CRMStatus.QUALIFIED
                print(f"[AIQualification] ✓ Qualified: {lead.company} (score: {lead.ai_score})")
            else:
                lead.status = LeadStatus.DISQUALIFIED
                print(f"[AIQualification] ✗ Disqualified: {lead.company} (reason: {research.qualification_reason})")

            await session.commit()
            return research.qualified

    async def qualify_campaign(self, campaign_id: int, batch_size: int = 10) -> dict:
        """Qualify all researched leads in a campaign."""
        from sqlalchemy import select, and_

        stats = {"qualified": 0, "disqualified": 0, "total": 0}

        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.campaign_id == campaign_id,
                        Lead.status == LeadStatus.RESEARCHED
                    )
                ).limit(batch_size)
            )
            leads = result.scalars().all()

        for lead in leads:
            is_qualified = await self.qualify_lead(lead.id)
            stats["total"] += 1
            if is_qualified:
                stats["qualified"] += 1
            else:
                stats["disqualified"] += 1

        print(f"[AIQualification] Campaign {campaign_id}: {stats}")
        return stats

    async def get_qualified_leads(self, campaign_id: int, limit: int = 100) -> list:
        """Get all qualified leads ready for outreach."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.campaign_id == campaign_id,
                        Lead.status == LeadStatus.QUALIFIED
                    )
                ).limit(limit)
            )
            return result.scalars().all()

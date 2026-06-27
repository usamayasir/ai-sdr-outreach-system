"""CRM: Track and manage lead lifecycle status."""
from database.connection import async_session
from database.models import Lead, CRMStatus, Campaign
from typing import List, Optional


class CRM:
    """Simple CRM for tracking lead status through the pipeline."""

    @staticmethod
    async def get_lead(lead_id: int) -> Optional[Lead]:
        """Get a lead by ID."""
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def update_status(lead_id: int, status: CRMStatus) -> bool:
        """Update a lead's CRM status."""
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if not lead:
                return False
            lead.crm_status = status
            await session.commit()
            print(f"[CRM] Lead {lead_id} → {status.value}")
            return True

    @staticmethod
    async def get_pipeline(campaign_id: int = None) -> dict:
        """Get pipeline breakdown by CRM status."""
        from sqlalchemy import select, func, and_

        stats = {}
        async with async_session() as session:
            for status in CRMStatus:
                if campaign_id:
                    result = await session.execute(
                        select(func.count(Lead.id)).where(
                            and_(Lead.crm_status == status, Lead.campaign_id == campaign_id)
                        )
                    )
                else:
                    result = await session.execute(
                        select(func.count(Lead.id)).where(Lead.crm_status == status)
                    )
                stats[status.value] = result.scalar() or 0
        return stats

    @staticmethod
    async def get_hot_leads(campaign_id: int = None, limit: int = 50) -> List[Lead]:
        """Get leads that are interested or meeting requested."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            query = select(Lead).where(
                Lead.crm_status.in_([CRMStatus.INTERESTED, CRMStatus.MEETING_REQUESTED, CRMStatus.TRIAL_STARTED])
            )
            if campaign_id:
                query = query.where(Lead.campaign_id == campaign_id)
            query = query.limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def get_leads_by_status(status: CRMStatus, campaign_id: int = None, limit: int = 100) -> List[Lead]:
        """Get leads filtered by status."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            query = select(Lead).where(Lead.crm_status == status)
            if campaign_id:
                query = query.where(Lead.campaign_id == campaign_id)
            query = query.limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def search_leads(search_term: str, limit: int = 50) -> List[Lead]:
        """Search leads by company name or email."""
        from sqlalchemy import select, or_

        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    or_(
                        Lead.company.ilike(f"%{search_term}%"),
                        Lead.email.ilike(f"%{search_term}%")
                    )
                ).limit(limit)
            )
            return result.scalars().all()

    @staticmethod
    async def get_campaign_stats(campaign_id: int) -> dict:
        """Get comprehensive stats for a campaign."""
        from sqlalchemy import select, func, and_

        async with async_session() as session:
            total = await session.execute(
                select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id)
            )
            qualified = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.campaign_id == campaign_id, Lead.ai_score >= 40)
                )
            )
            emails_sent = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.campaign_id == campaign_id, Lead.crm_status.in_([
                        CRMStatus.EMAIL_SENT, CRMStatus.OPENED, CRMStatus.CLICKED,
                        CRMStatus.INTERESTED, CRMStatus.MEETING_REQUESTED, CRMStatus.TRIAL_STARTED
                    ]))
                )
            )
            interested = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.campaign_id == campaign_id, Lead.crm_status.in_([
                        CRMStatus.INTERESTED, CRMStatus.MEETING_REQUESTED, CRMStatus.TRIAL_STARTED
                    ]))
                )
            )
            return {
                "total_leads": total.scalar() or 0,
                "qualified": qualified.scalar() or 0,
                "emails_sent": emails_sent.scalar() or 0,
                "interested": interested.scalar() or 0,
            }

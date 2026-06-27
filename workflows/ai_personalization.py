"""AI Personalization: Generate personalized email sequences for each qualified lead."""
from database.connection import async_session
from database.models import Lead, LeadResearch, EmailSequence, LeadStatus
from services.ai_service import AIService


class AIPersonalization:
    """Generate hyper-personalized outreach content for each lead."""

    def __init__(self):
        self.ai = AIService()

    async def generate_for_lead(self, lead_id: int) -> EmailSequence:
        """Generate personalized email sequence for a single lead."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if not lead:
                return None

            research_result = await session.execute(
                select(LeadResearch).where(LeadResearch.lead_id == lead_id)
            )
            research = research_result.scalar_one_or_none()
            if not research:
                print(f"[AIPersonalization] No research for lead {lead_id}")
                return None

            print(f"[AIPersonalization] Personalizing for: {lead.company}")

            ai_result = await self.ai.personalize_email(
                website_summary=research.website_summary or "",
                business_type=research.business_type or lead.category or "business",
                pain_points=research.pain_points or []
            )

            sequence = EmailSequence(
                lead_id=lead_id,
                subject=ai_result.get("subject", "Quick question about your business"),
                personalized_intro=ai_result.get("intro", ""),
                pain_point=ai_result.get("pain_point", ""),
                benefits=ai_result.get("benefits", ""),
                cta=ai_result.get("cta", "Would you be open to a quick 10-minute call?"),
                email_body=ai_result.get("email_body", ""),
                linkedin_message=ai_result.get("linkedin_message", ""),
                whatsapp_message=ai_result.get("whatsapp_message", ""),
            )

            session.add(sequence)
            await session.commit()
            await session.refresh(sequence)
            print(f"[AIPersonalization] ✓ Created sequence for: {lead.company}")
            return sequence

    async def generate_for_campaign(self, campaign_id: int, batch_size: int = 10) -> int:
        """Generate sequences for all qualified leads in a campaign."""
        from sqlalchemy import select, and_

        count = 0
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(
                    and_(
                        Lead.campaign_id == campaign_id,
                        Lead.status == LeadStatus.QUALIFIED
                    )
                ).limit(batch_size)
            )
            leads = result.scalars().all()

            for lead in leads:
                seq = await self.generate_for_lead(lead.id)
                if seq:
                    count += 1

        print(f"[AIPersonalization] Generated {count} sequences for campaign {campaign_id}")
        return count

    async def get_pending_sequences(self, campaign_id: int = None, limit: int = 50) -> list:
        """Get email sequences awaiting approval."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            if campaign_id:
                result = await session.execute(
                    select(EmailSequence).join(Lead).where(
                        and_(
                            EmailSequence.approved == False,
                            Lead.campaign_id == campaign_id
                        )
                    ).limit(limit)
                )
            else:
                result = await session.execute(
                    select(EmailSequence).where(
                        EmailSequence.approved == False
                    ).limit(limit)
                )
            return result.scalars().all()

    async def approve_sequence(self, sequence_id: int) -> bool:
        """Approve a sequence for sending."""
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with async_session() as session:
            result = await session.execute(
                select(EmailSequence).where(EmailSequence.id == sequence_id)
            )
            seq = result.scalar_one_or_none()
            if not seq:
                return False
            seq.approved = True
            seq.approved_at = datetime.now(timezone.utc)
            await session.commit()
            print(f"[AIPersonalization] Approved sequence {sequence_id}")
            return True

    async def bulk_approve(self, campaign_id: int = None) -> int:
        """Approve all pending sequences."""
        from sqlalchemy import select, and_
        from datetime import datetime, timezone

        async with async_session() as session:
            if campaign_id:
                result = await session.execute(
                    select(EmailSequence).join(Lead).where(
                        and_(
                            EmailSequence.approved == False,
                            Lead.campaign_id == campaign_id
                        )
                    )
                )
            else:
                result = await session.execute(
                    select(EmailSequence).where(EmailSequence.approved == False)
                )
            sequences = result.scalars().all()

            for seq in sequences:
                seq.approved = True
                seq.approved_at = datetime.now(timezone.utc)

            await session.commit()
            print(f"[AIPersonalization] Bulk approved {len(sequences)} sequences")
            return len(sequences)

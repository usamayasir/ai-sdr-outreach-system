"""Follow-up Engine: Automated follow-up sequence for non-responders."""
from datetime import datetime, timezone, timedelta
from database.connection import async_session
from database.models import Lead, EmailLog, FollowUp, OutreachStatus, CRMStatus
from services.ai_service import AIService
from services.smartlead import SmartleadService
from config.settings import get_settings


class FollowUpEngine:
    """Manage 3-step follow-up sequence (Day 3, Day 7, Day 14)."""

    def __init__(self):
        self.ai = AIService()
        self.smartlead = SmartleadService()
        self.settings = get_settings()
        self.followup_days = [int(d.strip()) for d in self.settings.followup_days.split(",")]

    async def process_pending_followups(self) -> int:
        """Check and send any follow-ups that are due."""
        from sqlalchemy import select, and_

        sent_count = 0
        async with async_session() as session:
            result = await session.execute(
                select(FollowUp).where(
                    and_(
                        FollowUp.status == "pending",
                        FollowUp.scheduled_at <= datetime.now(timezone.utc)
                    )
                )
            )
            followups = result.scalars().all()

        for followup in followups:
            sent = await self._send_followup(followup.id)
            if sent:
                sent_count += 1

        print(f"[FollowUpEngine] Sent {sent_count} follow-ups")
        return sent_count

    async def _send_followup(self, followup_id: int) -> bool:
        """Send a single follow-up email."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(FollowUp).where(FollowUp.id == followup_id))
            followup = result.scalar_one_or_none()
            if not followup or followup.status != "pending":
                return False

            lead = followup.lead
            email_log = followup.email_log

            if not lead or not lead.email:
                return False

            # Get email history for context
            email_history = ""
            if email_log and email_log.sequence:
                email_history = f"Original: {email_log.sequence.email_body}"

            # Generate follow-up content
            followup_data = await self.ai.generate_followup(
                email_history=email_history,
                followup_number=followup.followup_number
            )

            # Send via Smartlead
            response = await self.smartlead.send_email(
                to_email=lead.email,
                subject=followup_data.get("subject", "Quick follow-up"),
                body=followup_data.get("body", "Just following up on my previous email."),
                campaign_id=self.settings.smartlead_campaign_id
            )

            followup.sent_at = datetime.now(timezone.utc)
            followup.status = "sent"
            await session.commit()
            print(f"[FollowUpEngine] ✓ Follow-up #{followup.followup_number} sent to {lead.company}")
            return True

    async def schedule_followups(self, email_log_id: int) -> int:
        """Schedule follow-up sequence for an email that was sent."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(EmailLog).where(EmailLog.id == email_log_id))
            log = result.scalar_one_or_none()
            if not log or not log.sent_at:
                return 0

            # Don't schedule if already replied
            if log.status == OutreachStatus.REPLIED:
                print(f"[FollowUpEngine] Skipping followups for {log.lead_id} — already replied")
                return 0

            count = 0
            for i, days in enumerate(self.followup_days, 1):
                scheduled_at = log.sent_at + timedelta(days=days)
                followup = FollowUp(
                    lead_id=log.lead_id,
                    email_log_id=log.id,
                    followup_number=i,
                    scheduled_at=scheduled_at,
                    status="pending"
                )
                session.add(followup)
                count += 1

            await session.commit()
            print(f"[FollowUpEngine] Scheduled {count} follow-ups for email log {email_log_id}")
            return count

    async def stop_followups(self, lead_id: int) -> int:
        """Stop all pending follow-ups for a lead (e.g. after reply)."""
        from sqlalchemy import select, update

        async with async_session() as session:
            result = await session.execute(
                select(FollowUp).where(
                    FollowUp.lead_id == lead_id,
                    FollowUp.status == "pending"
                )
            )
            followups = result.scalars().all()

            for f in followups:
                f.status = "stopped"

            await session.commit()
            print(f"[FollowUpEngine] Stopped {len(followups)} follow-ups for lead {lead_id}")
            return len(followups)

    async def get_overdue_followups(self) -> list:
        """Get follow-ups that are past due but not sent."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(FollowUp).where(
                    and_(
                        FollowUp.status == "pending",
                        FollowUp.scheduled_at < datetime.now(timezone.utc) - timedelta(days=1)
                    )
                )
            )
            return result.scalars().all()

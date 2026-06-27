"""Email Campaign: Send personalized emails via Smartlead with rate limiting and tracking."""
from datetime import datetime, timezone
from database.connection import async_session
from database.models import (
    Lead, EmailSequence, EmailLog, Campaign, OutreachStatus, CRMStatus, LeadStatus
)
from services.smartlead import SmartleadService
from services.ai_service import AIService
from config.settings import get_settings


class EmailCampaign:
    """Manage email sending, tracking, and daily batch limits."""

    def __init__(self):
        self.smartlead = SmartleadService()
        self.ai = AIService()
        self.settings = get_settings()

    async def send_daily_batch(self, limit: int = None) -> dict:
        """Send approved emails up to the daily limit."""
        limit = limit or self.settings.daily_email_limit
        from sqlalchemy import select, and_, func

        sent_count = 0
        errors = 0

        async with async_session() as session:
            # Count already sent today
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            result = await session.execute(
                select(func.count(EmailLog.id)).where(
                    and_(
                        EmailLog.sent_at >= today,
                        EmailLog.status == OutreachStatus.SENT
                    )
                )
            )
            already_sent = result.scalar() or 0
            remaining = limit - already_sent

            if remaining <= 0:
                print(f"[EmailCampaign] Daily limit reached ({already_sent}/{limit})")
                return {"sent": 0, "remaining": 0, "limit": limit}

            # Get approved sequences not yet sent
            result = await session.execute(
                select(EmailSequence).where(
                    and_(
                        EmailSequence.approved == True,
                        EmailSequence.id.notin_(
                            select(EmailLog.sequence_id).where(EmailLog.sequence_id.isnot(None))
                        )
                    )
                ).limit(remaining)
            )
            sequences = result.scalars().all()

        for seq in sequences:
            try:
                await self._send_sequence(seq)
                sent_count += 1
            except Exception as e:
                print(f"[EmailCampaign] Error sending to {seq.lead_id}: {e}")
                errors += 1

        print(f"[EmailCampaign] Sent {sent_count} emails today ({already_sent + sent_count}/{limit})")
        return {"sent": sent_count, "remaining": remaining - sent_count, "limit": limit, "errors": errors}

    async def _send_sequence(self, seq: EmailSequence) -> EmailLog:
        """Send a single email sequence."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Lead).where(Lead.id == seq.lead_id))
            lead = result.scalar_one_or_none()
            if not lead or not lead.email:
                raise ValueError(f"Lead {seq.lead_id} has no email")

            print(f"[EmailCampaign] Sending to {lead.company} <{lead.email}>")

            response = await self.smartlead.send_email(
                to_email=lead.email,
                subject=seq.subject,
                body=seq.email_body,
                campaign_id=self.settings.smartlead_campaign_id
            )

            log = EmailLog(
                lead_id=lead.id,
                sequence_id=seq.id,
                status=OutreachStatus.SENT,
                sent_at=datetime.now(timezone.utc),
                smartlead_message_id=response.get("message_id", ""),
                followup_number=0
            )
            session.add(log)

            lead.crm_status = CRMStatus.EMAIL_SENT
            await session.commit()
            await session.refresh(log)
            print(f"[EmailCampaign] ✓ Sent to {lead.company}")
            return log

    async def send_single(self, lead_id: int, sequence_id: int = None) -> dict:
        """Manually send a single email."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if not lead:
                return {"error": "Lead not found"}

            if sequence_id:
                result = await session.execute(select(EmailSequence).where(EmailSequence.id == sequence_id))
                seq = result.scalar_one_or_none()
            else:
                result = await session.execute(
                    select(EmailSequence).where(EmailSequence.lead_id == lead_id).order_by(EmailSequence.id.desc())
                )
                seq = result.scalar_one_or_none()

            if not seq:
                return {"error": "No email sequence found for this lead"}

            if not seq.approved:
                seq.approved = True

            try:
                log = await self._send_sequence(seq)
                return {"success": True, "log_id": log.id, "message_id": log.smartlead_message_id}
            except Exception as e:
                return {"error": str(e)}

    # ── Webhook Handlers ─────────────────────────────────────

    async def handle_open(self, email: str, message_id: str) -> bool:
        """Process email open event from Smartlead webhook."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(EmailLog).where(
                    and_(
                        EmailLog.smartlead_message_id == message_id,
                        EmailLog.lead.has(Lead.email == email)
                    )
                )
            )
            log = result.scalar_one_or_none()
            if not log:
                return False

            log.opened_at = datetime.now(timezone.utc)
            log.status = OutreachStatus.OPENED
            log.lead.crm_status = CRMStatus.OPENED
            await session.commit()
            print(f"[EmailCampaign] ✉ Opened by {email}")
            return True

    async def handle_click(self, email: str, message_id: str) -> bool:
        """Process email click event from Smartlead webhook."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(EmailLog).where(
                    and_(
                        EmailLog.smartlead_message_id == message_id,
                        EmailLog.lead.has(Lead.email == email)
                    )
                )
            )
            log = result.scalar_one_or_none()
            if not log:
                return False

            log.clicked_at = datetime.now(timezone.utc)
            log.status = OutreachStatus.CLICKED
            log.lead.crm_status = CRMStatus.CLICKED
            await session.commit()
            print(f"[EmailCampaign] 🖱 Clicked by {email}")
            return True

    async def handle_bounce(self, email: str, message_id: str) -> bool:
        """Process bounce event."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            result = await session.execute(
                select(EmailLog).where(
                    and_(
                        EmailLog.smartlead_message_id == message_id,
                        EmailLog.lead.has(Lead.email == email)
                    )
                )
            )
            log = result.scalar_one_or_none()
            if not log:
                return False

            log.bounced_at = datetime.now(timezone.utc)
            log.status = OutreachStatus.BOUNCED
            await session.commit()
            print(f"[EmailCampaign] ⚠ Bounced: {email}")
            return True

    # ── Stats ────────────────────────────────────────────────

    async def get_stats(self, campaign_id: int = None) -> dict:
        """Get campaign email statistics."""
        from sqlalchemy import select, func, and_

        async with async_session() as session:
            stats = {}
            for status in OutreachStatus:
                if campaign_id:
                    result = await session.execute(
                        select(func.count(EmailLog.id)).where(
                            and_(
                                EmailLog.status == status,
                                EmailLog.lead.has(Lead.campaign_id == campaign_id)
                            )
                        )
                    )
                else:
                    result = await session.execute(
                        select(func.count(EmailLog.id)).where(EmailLog.status == status)
                    )
                stats[status.value] = result.scalar() or 0
            return stats

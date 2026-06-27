"""Reply Manager: Handle prospect replies with AI classification and draft responses."""
from datetime import datetime, timezone
from database.connection import async_session
from database.models import (
    Lead, EmailLog, Reply, ReplyCategory, OutreachStatus, CRMStatus
)
from services.ai_service import AIService


class ReplyManager:
    """Process incoming replies, classify them, and draft AI responses."""

    def __init__(self):
        self.ai = AIService()

    async def process_reply(self, email: str, content: str, message_id: str = None, email_log_id: int = None) -> Reply:
        """Process a new reply from a prospect."""
        from sqlalchemy import select, and_

        async with async_session() as session:
            # Find the lead and associated email log
            result = await session.execute(select(Lead).where(Lead.email == email))
            lead = result.scalar_one_or_none()
            if not lead:
                print(f"[ReplyManager] Lead not found for email: {email}")
                return None

            # Get email history for context
            email_history = ""
            if email_log_id:
                log_result = await session.execute(
                    select(EmailLog).where(EmailLog.id == email_log_id)
                )
                log = log_result.scalar_one_or_none()
            else:
                log_result = await session.execute(
                    select(EmailLog).where(
                        and_(
                            EmailLog.lead_id == lead.id,
                            EmailLog.status.in_([OutreachStatus.SENT, OutreachStatus.OPENED, OutreachStatus.CLICKED])
                        )
                    ).order_by(EmailLog.sent_at.desc())
                )
                log = log_result.scalar_one_or_none()

            if log:
                email_history = f"Subject: {log.sequence.subject if log.sequence else ''}\nBody: {log.sequence.email_body if log.sequence else ''}"
                log.replied_at = datetime.now(timezone.utc)
                log.status = OutreachStatus.REPLIED

            # AI classification
            category_str = await self.ai.categorize_reply(content)
            try:
                category = ReplyCategory(category_str)
            except ValueError:
                category = ReplyCategory.QUESTION

            sentiment = await self.ai.analyze_sentiment(content)

            # AI draft reply
            business_info = f"Company: {lead.company}, Category: {lead.category or ''}"
            draft = await self.ai.draft_reply(content, category.value, email_history, business_info)

            reply = Reply(
                lead_id=lead.id,
                email_log_id=log.id if log else None,
                content=content,
                category=category,
                sentiment_score=sentiment,
                ai_draft_reply=draft,
                approved=False
            )
            session.add(reply)

            # Update CRM status based on category
            if category == ReplyCategory.INTERESTED:
                lead.crm_status = CRMStatus.INTERESTED
            elif category == ReplyCategory.NOT_INTERESTED:
                lead.crm_status = CRMStatus.LOST
            elif category == ReplyCategory.QUESTION:
                lead.crm_status = CRMStatus.INTERESTED

            await session.commit()
            await session.refresh(reply)
            print(f"[ReplyManager] ✓ Reply from {lead.company}: {category.value} (sentiment: {sentiment:.2f})")
            return reply

    async def get_pending_replies(self, limit: int = 50) -> list:
        """Get replies awaiting approval to send."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(Reply).where(
                    Reply.approved == False
                ).limit(limit)
            )
            return result.scalars().all()

    async def approve_reply(self, reply_id: int) -> bool:
        """Approve an AI draft reply to be sent."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Reply).where(Reply.id == reply_id))
            reply = result.scalar_one_or_none()
            if not reply:
                return False

            reply.approved = True
            reply.sent_at = datetime.now(timezone.utc)
            await session.commit()
            print(f"[ReplyManager] Approved reply {reply_id}")
            return True

    async def get_reply_stats(self) -> dict:
        """Get reply statistics."""
        from sqlalchemy import select, func

        async with async_session() as session:
            stats = {}
            for cat in ReplyCategory:
                result = await session.execute(
                    select(func.count(Reply.id)).where(Reply.category == cat)
                )
                stats[cat.value] = result.scalar() or 0
            return stats

    async def auto_reply(self, reply_id: int) -> bool:
        """Auto-send reply for certain categories (e.g. OOO, spam)."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Reply).where(Reply.id == reply_id))
            reply = result.scalar_one_or_none()
            if not reply:
                return False

            # Auto-approve and mark as sent for non-interesting categories
            if reply.category in [ReplyCategory.OOO, ReplyCategory.SPAM, ReplyCategory.NOT_INTERESTED]:
                reply.approved = True
                reply.sent_at = datetime.now(timezone.utc)
                await session.commit()
                print(f"[ReplyManager] Auto-handled {reply.category.value} reply {reply_id}")
                return True
            return False

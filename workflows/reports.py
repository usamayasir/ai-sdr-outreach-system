"""Reports: Generate daily and on-demand performance reports."""
from datetime import datetime, timezone, timedelta
from database.connection import async_session
from database.models import (
    Lead, EmailLog, Reply, FollowUp, DailyReport, Campaign, OutreachStatus, ReplyCategory, CRMStatus
)
from services.ai_service import AIService


class ReportEngine:
    """Generate comprehensive analytics reports."""

    def __init__(self):
        self.ai = AIService()

    async def generate_daily_report(self, date: datetime = None) -> str:
        """Generate a formatted daily report for a given date."""
        from sqlalchemy import select, func, and_

        date = date or datetime.now(timezone.utc)
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        async with async_session() as session:
            # Leads found today
            leads_found = await session.execute(
                select(func.count(Lead.id)).where(Lead.created_at.between(start, end))
            )
            leads_found = leads_found.scalar() or 0

            # Qualified today
            qualified = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.status == "qualified", Lead.created_at.between(start, end))
                )
            )
            qualified = qualified.scalar() or 0

            # Emails sent today
            emails_sent = await session.execute(
                select(func.count(EmailLog.id)).where(
                    EmailLog.sent_at.between(start, end)
                )
            )
            emails_sent = emails_sent.scalar() or 0

            # Opens today
            emails_opened = await session.execute(
                select(func.count(EmailLog.id)).where(
                    EmailLog.opened_at.between(start, end)
                )
            )
            emails_opened = emails_opened.scalar() or 0

            # Clicks today
            emails_clicked = await session.execute(
                select(func.count(EmailLog.id)).where(
                    EmailLog.clicked_at.between(start, end)
                )
            )
            emails_clicked = emails_clicked.scalar() or 0

            # Replies today
            replies = await session.execute(
                select(func.count(Reply.id)).where(Reply.created_at.between(start, end))
            )
            replies = replies.scalar() or 0

            # Interested replies
            interested = await session.execute(
                select(func.count(Reply.id)).where(
                    and_(Reply.category == ReplyCategory.INTERESTED, Reply.created_at.between(start, end))
                )
            )
            interested = interested.scalar() or 0

            # Meetings/trials
            meetings = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.crm_status == CRMStatus.MEETING_REQUESTED, Lead.updated_at.between(start, end))
                )
            )
            meetings = meetings.scalar() or 0

            trials = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.crm_status == CRMStatus.TRIAL_STARTED, Lead.updated_at.between(start, end))
                )
            )
            trials = trials.scalar() or 0

        # Build report
        report = f"""📊 Daily Report — {start.strftime('%Y-%m-%d')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 ACTIVITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Leads Found: {leads_found}
• Qualified: {qualified}
• Emails Sent: {emails_sent}
• Emails Opened: {emails_opened}
• Emails Clicked: {emails_clicked}
• Replies Received: {replies}
• Interested Replies: {interested}
• Meetings Booked: {meetings}
• Trials Started: {trials}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 RATES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Open Rate: {(emails_opened / emails_sent * 100) if emails_sent else 0:.1f}%
• Reply Rate: {(replies / emails_sent * 100) if emails_sent else 0:.1f}%
• Interest Rate: {(interested / emails_sent * 100) if emails_sent else 0:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        # Save to database
        async with async_session() as session:
            dr = DailyReport(
                report_date=start,
                leads_found=leads_found,
                qualified=qualified,
                emails_sent=emails_sent,
                emails_opened=emails_opened,
                emails_clicked=emails_clicked,
                replies=replies,
                interested=interested,
                meetings_booked=meetings,
                trials_started=trials
            )
            session.add(dr)
            await session.commit()

        return report

    async def generate_weekly_summary(self) -> str:
        """Generate a 7-day rolling summary."""
        from sqlalchemy import select, func, and_

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)

        async with async_session() as session:
            leads_found = await session.execute(
                select(func.count(Lead.id)).where(Lead.created_at.between(start, end))
            )
            emails_sent = await session.execute(
                select(func.count(EmailLog.id)).where(EmailLog.sent_at.between(start, end))
            )
            replies = await session.execute(
                select(func.count(Reply.id)).where(Reply.created_at.between(start, end))
            )
            interested = await session.execute(
                select(func.count(Reply.id)).where(
                    and_(Reply.category == ReplyCategory.INTERESTED, Reply.created_at.between(start, end))
                )
            )

        return f"""📊 Weekly Summary ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')})

• Leads Found: {leads_found.scalar() or 0}
• Emails Sent: {emails_sent.scalar() or 0}
• Replies: {replies.scalar() or 0}
• Interested: {interested.scalar() or 0}
"""

    async def get_campaign_report(self, campaign_id: int) -> str:
        """Get detailed report for a specific campaign."""
        from sqlalchemy import select, func, and_

        async with async_session() as session:
            result = await session.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalar_one_or_none()
            if not campaign:
                return "Campaign not found."

            total_leads = await session.execute(
                select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id)
            )
            total_leads = total_leads.scalar() or 0

            qualified = await session.execute(
                select(func.count(Lead.id)).where(
                    and_(Lead.campaign_id == campaign_id, Lead.status == "qualified")
                )
            )
            qualified = qualified.scalar() or 0

            emails_sent = await session.execute(
                select(func.count(EmailLog.id)).where(
                    EmailLog.lead.has(Lead.campaign_id == campaign_id)
                )
            )
            emails_sent = emails_sent.scalar() or 0

            return f"""📊 Campaign Report: {campaign.name}

• Target: {campaign.target_leads}
• Total Leads: {total_leads}
• Qualified: {qualified}
• Emails Sent: {emails_sent}
• Status: {campaign.status}
"""

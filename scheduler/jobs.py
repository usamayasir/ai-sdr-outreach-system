"""Scheduler: Background job runner for daily automation."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
from workflows.email_campaign import EmailCampaign
from workflows.followup_engine import FollowUpEngine
from workflows.reports import ReportEngine
from workflows.content_engine import ContentEngine
from bot.telegram_bot import TelegramControlCenter
from config.settings import get_settings


class JobScheduler:
    """Cron-based scheduler for all background tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.settings = get_settings()

    async def start(self):
        """Start all scheduled jobs."""
        # Daily report at 9 PM
        self.scheduler.add_job(
            self.send_daily_report,
            CronTrigger(hour=21, minute=0, timezone=self.settings.timezone)
        )

        # Content generation at 8 AM
        self.scheduler.add_job(
            self.generate_content,
            CronTrigger(hour=8, minute=0, timezone=self.settings.timezone)
        )

        # Follow-up checks every 2 hours
        self.scheduler.add_job(
            self.process_followups,
            'interval', hours=2
        )

        # Email sending batch every 15 minutes during business hours
        self.scheduler.add_job(
            self.send_email_batch,
            'interval', minutes=15
        )

        self.scheduler.start()
        print(f"[Scheduler] Started with {len(self.scheduler.get_jobs())} jobs")

    async def send_daily_report(self):
        """Generate and send daily report via Telegram."""
        try:
            engine = ReportEngine()
            report = await engine.generate_daily_report()
            bot = TelegramControlCenter()
            await bot.app.bot.send_message(
                chat_id=self.settings.telegram_admin_id,
                text=report
            )
            print("[Scheduler] Daily report sent")
        except Exception as e:
            print(f"[Scheduler] Error sending report: {e}")

    async def generate_content(self):
        """Generate daily content pieces."""
        try:
            engine = ContentEngine()
            await engine.generate_daily_content()
            print("[Scheduler] Content generated")
        except Exception as e:
            print(f"[Scheduler] Error generating content: {e}")

    async def process_followups(self):
        """Process pending follow-up emails."""
        try:
            engine = FollowUpEngine()
            count = await engine.process_pending_followups()
            print(f"[Scheduler] {count} follow-ups processed")
        except Exception as e:
            print(f"[Scheduler] Error processing followups: {e}")

    async def send_email_batch(self):
        """Send daily batch of approved emails."""
        try:
            engine = EmailCampaign()
            result = await engine.send_daily_batch()
            print(f"[Scheduler] Email batch: {result}")
        except Exception as e:
            print(f"[Scheduler] Error sending emails: {e}")

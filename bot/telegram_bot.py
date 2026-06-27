"""Telegram Control Center: Bot for managing the AI SDR system."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from config.settings import get_settings
from database.connection import async_session
from database.models import (
    Campaign, Lead, EmailSequence, EmailLog, Reply, FollowUp,
    DailyReport, LeadStatus, CampaignStatus, CRMStatus, OutreachStatus
)
from workflows.lead_hunter import LeadHunter
from workflows.website_research import WebsiteResearch
from workflows.ai_qualification import AIQualification
from workflows.ai_personalization import AIPersonalization
from workflows.email_campaign import EmailCampaign
from workflows.reply_manager import ReplyManager
from workflows.followup_engine import FollowUpEngine
from workflows.crm import CRM
from workflows.reports import ReportEngine
from workflows.content_engine import ContentEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramControlCenter:
    """Telegram bot for controlling the AI SDR system."""

    def __init__(self):
        settings = get_settings()
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        self.admin_id = settings.telegram_admin_id
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("find", self.cmd_find))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("report", self.cmd_report))
        self.app.add_handler(CommandHandler("campaigns", self.cmd_campaigns))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause))
        self.app.add_handler(CommandHandler("resume", self.cmd_resume))
        self.app.add_handler(CommandHandler("send", self.cmd_send))
        self.app.add_handler(CommandHandler("pipeline", self.cmd_pipeline))
        self.app.add_handler(CommandHandler("hot", self.cmd_hot_leads))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

    async def _is_admin(self, update: Update) -> bool:
        return update.effective_user.id == self.admin_id

    async def _send(self, update: Update, text: str):
        """Safe send with error handling."""
        try:
            await update.message.reply_text(text)
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

    # ── Commands ─────────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        await self._send(update,
            "🤖 AI SDR Control Center\n\n"
            "Commands:\n"
            "/find <industry> <country> <city> <target> — Start lead hunting\n"
            "/status — System status\n"
            "/report — Daily report\n"
            "/campaigns — List campaigns\n"
            "/pipeline — Sales pipeline\n"
            "/hot — Hot leads (interested)\n"
            "/pause — Pause campaigns\n"
            "/resume — Resume campaigns\n"
            "/send — Approve & send emails\n"
            "/help — Show this help"
        )

    async def cmd_find(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        args = context.args
        if len(args) < 4:
            await self._send(update,
                "Usage: /find <industry> <country> <city> <target_leads>\n"
                "Example: /find Dental-Clinics Pakistan Karachi 300"
            )
            return

        industry, country, city, target = args[0], args[1], args[2], int(args[3])

        # Create campaign
        async with async_session() as session:
            campaign = Campaign(
                name=f"{industry} - {city}",
                industry=industry,
                country=country,
                city=city,
                target_leads=target
            )
            session.add(campaign)
            await session.commit()
            await session.refresh(campaign)

        await self._send(update,
            f"🎯 Campaign created: {campaign.name}\n"
            f"Target: {target} leads\n"
            f"Starting lead hunting..."
        )

        # Run lead hunter
        hunter = LeadHunter()
        leads = await hunter.hunt(industry, country, city, target)
        await hunter.save_to_db(campaign.id, leads)

        await self._send(update,
            f"✓ Found {len(leads)} leads!\n"
            f"Starting website research..."
        )

        # Website research
        research = WebsiteResearch()
        await research.process_campaign(campaign.id, batch_size=20)

        await self._send(update,
            f"✓ Website research complete!\n"
            f"Starting AI qualification..."
        )

        # AI qualification
        qualifier = AIQualification()
        stats = await qualifier.qualify_campaign(campaign.id, batch_size=20)

        await self._send(update,
            f"✓ AI Qualification complete!\n"
            f"Qualified: {stats['qualified']}\n"
            f"Disqualified: {stats['disqualified']}\n"
            f"Starting AI personalization..."
        )

        # AI personalization
        personalizer = AIPersonalization()
        count = await personalizer.generate_for_campaign(campaign.id, batch_size=20)

        await self._send(update,
            f"✓ AI Personalization complete!\n"
            f"Generated {count} email sequences\n\n"
            f"Use /send to approve and send emails."
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        from sqlalchemy import func, select

        async with async_session() as session:
            lead_count = await session.scalar(select(func.count(Lead.id)))
            sent_count = await session.scalar(
                select(func.count(EmailLog.id)).where(EmailLog.status == OutreachStatus.SENT)
            )
            reply_count = await session.scalar(select(func.count(Reply.id)))
            open_count = await session.scalar(
                select(func.count(EmailLog.id)).where(EmailLog.status == OutreachStatus.OPENED)
            )
            click_count = await session.scalar(
                select(func.count(EmailLog.id)).where(EmailLog.status == OutreachStatus.CLICKED)
            )
            pending_seq = await session.scalar(
                select(func.count(EmailSequence.id)).where(EmailSequence.approved == False)
            )

        text = (
            f"📊 System Status\n\n"
            f"Total Leads: {lead_count or 0}\n"
            f"Emails Sent: {sent_count or 0}\n"
            f"Opened: {open_count or 0}\n"
            f"Clicked: {click_count or 0}\n"
            f"Replies: {reply_count or 0}\n"
            f"Pending Approval: {pending_seq or 0}\n"
            f"Status: 🟢 Active"
        )
        await self._send(update, text)

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        engine = ReportEngine()
        report = await engine.generate_daily_report()
        await self._send(update, report)

    async def cmd_campaigns(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Campaign).order_by(Campaign.created_at.desc()).limit(10))
            campaigns = result.scalars().all()

        if not campaigns:
            await self._send(update, "No campaigns yet.")
            return

        text = "📋 Campaigns:\n\n"
        for c in campaigns:
            text += f"• {c.name} — {c.status.value} — Target: {c.target_leads}\n"
        await self._send(update, text)

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        from sqlalchemy import update
        async with async_session() as session:
            await session.execute(update(Campaign).values(status=CampaignStatus.PAUSED))
            await session.commit()
        await self._send(update, "⏸ All campaigns paused.")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        from sqlalchemy import update
        async with async_session() as session:
            await session.execute(update(Campaign).values(status=CampaignStatus.ACTIVE))
            await session.commit()
        await self._send(update, "▶ All campaigns resumed.")

    async def cmd_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(EmailSequence).where(EmailSequence.approved == False).limit(10)
            )
            pending = result.scalars().all()

            if not pending:
                await self._send(update, "No pending approvals.\nUse /find to create a campaign.")
                return

            keyboard = [
                [InlineKeyboardButton(f"✓ Approve {p.lead.company}", callback_data=f"approve_{p.id}")]
                for p in pending[:5]
            ]
            keyboard.append([InlineKeyboardButton("✓✓ Approve ALL", callback_data="approve_all")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self._send(update, f"{len(pending)} emails pending approval. Top 5:")
            await update.message.reply_text("Choose to approve:", reply_markup=reply_markup)

    async def cmd_pipeline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        stats = await CRM.get_pipeline()
        text = "🚦 Sales Pipeline\n\n"
        for status, count in stats.items():
            text += f"• {status}: {count}\n"
        await self._send(update, text)

    async def cmd_hot_leads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._is_admin(update):
            return
        leads = await CRM.get_hot_leads(limit=10)
        if not leads:
            await self._send(update, "No hot leads yet.")
            return

        text = "🔥 Hot Leads:\n\n"
        for lead in leads:
            text += f"• {lead.company} — {lead.email} — {lead.crm_status.value}\n"
        await self._send(update, text)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_start(update, context)

    # ── Callback Handlers ────────────────────────────────────

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith("approve_"):
            if data == "approve_all":
                personalizer = AIPersonalization()
                count = await personalizer.bulk_approve()
                await query.edit_message_text(f"✓ Approved {count} emails! They will be sent in the next batch.")
            else:
                seq_id = int(data.split("_")[1])
                personalizer = AIPersonalization()
                await personalizer.approve_sequence(seq_id)
                await query.edit_message_text(f"✓ Approved! Email will be sent in the next batch.")

    def run(self):
        self.app.run_polling()

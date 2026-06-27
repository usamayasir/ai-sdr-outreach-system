# 🤖 AI SDR Outreach System

A fully autonomous **Sales Development Representative (SDR)** system built for the **Kimi Work** ecosystem. It hunts leads, researches websites, qualifies prospects with AI, generates hyper-personalized emails, manages campaigns, handles replies, and sends follow-ups — all controlled via a Telegram bot.

---

## 🏗 Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Lead Hunter  │────▶│ Firecrawl    │────▶│ AI Qualify   │
│ (Google/API) │     │ (Website)    │     │ (Kimi AI)    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
┌──────────────┐     ┌──────────────┐     ┌──────▼───────┐
│ Reply Mgr    │◀────│ Smartlead    │◀────│ AI Personalize│
│ (Draft)      │     │ (Send)       │     │ (Kimi AI)    │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
┌──────▼───────┐     ┌──────────────┐     ┌──────────────┐
│ Follow-up    │────▶│ CRM &        │────▶│ Telegram     │
│ Engine       │     │ Reports      │     │ Bot Control  │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 🚀 Tech Stack

| Layer | Technology |
|-------|------------|
| **Database** | Supabase (PostgreSQL) + SQLAlchemy Async |
| **AI** | Kimi (Moonshot AI) via OpenAI-compatible API |
| **Lead Hunting** | Google Places API + Apollo.io (optional) |
| **Website Research** | Firecrawl.dev |
| **Email Delivery** | Smartlead.ai |
| **Scheduling** | APScheduler (cron jobs) |
| **Control Center** | Telegram Bot (python-telegram-bot) |
| **Container** | Docker + Docker Compose |

---

## 📁 Project Structure

```
ai-sdr/
├── config/
│   └── settings.py          # Pydantic settings (env vars)
├── database/
│   ├── connection.py        # Async SQLAlchemy engine
│   └── models.py            # 12 ORM models (Campaign, Lead, EmailLog, etc.)
├── services/
│   ├── ai_service.py        # Kimi AI wrapper (qualify, personalize, draft, content)
│   ├── firecrawl.py         # Website scraping & business intelligence
│   ├── smartlead.py         # Email sending & campaign analytics
│   └── sheets.py            # Google Sheets export (optional review)
├── workflows/
│   ├── lead_hunter.py       # Google Places + Apollo lead discovery
│   ├── website_research.py  # Batch website scraping
│   ├── ai_qualification.py  # AI-powered lead scoring
│   ├── ai_personalization.py # Hyper-personalized email generation
│   ├── email_campaign.py    # Send, track, webhook handling
│   ├── reply_manager.py     # Classify replies & draft AI responses
│   ├── followup_engine.py   # 3-step automated follow-up (3/7/14 days)
│   ├── crm.py               # Pipeline & status tracking
│   ├── reports.py           # Daily & weekly analytics
│   └── content_engine.py    # LinkedIn, Facebook, blog content generation
├── bot/
│   └── telegram_bot.py      # Full control center via Telegram
├── scheduler/
│   └── jobs.py              # Cron jobs (email batch, follow-ups, reports, content)
├── main.py                  # Entry point
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## ⚡ Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/usamayasir/ai-sdr-outreach-system.git
cd ai-sdr-outreach-system
cp .env.example .env
# Edit .env with your API keys
```

### 2. Database Setup (Supabase)

The system auto-creates tables on first run. Just point `DATABASE_URL` to your Supabase connection string.

### 3. Run

```bash
# Docker (recommended)
docker-compose up --build

# Or locally
pip install -r requirements.txt
python main.py
```

---

## 🤖 Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/find <industry> <country> <city> <target>` | Launch a full campaign: hunt → research → qualify → personalize |
| `/status` | System stats: leads, sent, opened, replies |
| `/report` | Daily performance report |
| `/campaigns` | List active campaigns |
| `/pipeline` | Full CRM pipeline view |
| `/hot` | Hot leads (interested/meeting) |
| `/send` | Approve pending emails |
| `/pause` / `/resume` | Pause or resume campaigns |
| `/help` | Show all commands |

---

## 🔗 API Keys Needed

| Service | Key | Get From |
|---------|-----|----------|
| **Kimi AI** | `AI_API_KEY` | [platform.moonshot.cn](https://platform.moonshot.cn) |
| **Smartlead** | `SMARTLEAD_API_KEY` | [smartlead.ai](https://smartlead.ai) |
| **Firecrawl** | `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) |
| **Google Places** | `GOOGLE_MAPS_API_KEY` | [Google Cloud Console](https://console.cloud.google.com) |
| **Apollo.io** | `APOLLO_API_KEY` | *(optional, for enrichment)* |
| **Telegram Bot** | `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |

---

## 📊 Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `campaigns` | Campaign definitions (industry, country, city, target) |
| `leads` | Discovered business leads with contact info |
| `lead_research` | Website intelligence (has chat, AI score, pain points) |
| `email_sequences` | AI-generated personalized emails |
| `email_logs` | Send tracking (sent, opened, clicked, replied, bounced) |
| `replies` | Incoming replies with AI classification & draft |
| `followups` | Scheduled 3-step follow-up sequence |
| `daily_reports` | Daily analytics snapshots |
| `content_pieces` | Generated blog/LinkedIn/Facebook content |

---

## 🔧 AI Prompts (Built-in)

### Qualification Prompt
```
Analyze this business website and determine if they already have an AI chatbot.
Respond ONLY in JSON with: has_live_chat, has_ai_chat, chat_tools, qualified, reason, ai_score
"qualified" = TRUE only if they DON'T have AI chat (our target market).
```

### Personalization Prompt
```
Write a personalized cold email for this business.
Create: subject, intro, pain_point, benefits, cta, email_body, linkedin_message, whatsapp_message
```

### Reply Classification Prompt
```
Categorize this email reply into: interested, question, not_interested, spam, ooo
```

### Draft Reply Prompt
```
Draft a professional reply based on category.
Interested → suggest meeting times. Question → answer clearly. Not interested → polite close.
```

---

## 🔄 Automation Schedule

| Job | Frequency | Time |
|-----|-----------|------|
| Email batch sending | Every 15 minutes | — |
| Follow-up processing | Every 2 hours | — |
| Daily report | Once daily | 21:00 |
| Content generation | Once daily | 08:00 |

---

## 🛠 Built for Kimi Work

This system leverages the **Kimi Work** ecosystem:

- **Supabase MCP** → PostgreSQL database (schema, queries, migrations)
- **GitHub MCP** → Code repository management
- **Kimi WebBridge** → Browser-based lead research (fallback for scraping)
- **Kimi Cron** → Scheduled job execution (reports, follow-ups, content)
- **Kimi AI** → All AI tasks (qualification, personalization, drafting, content)

---

## 📝 License

MIT

## 👤 Author

Built by [Usama Yasir](https://github.com/usamayasir) for the Kimi Work ecosystem.

---

*"Let AI do the hunting, while you close the deals."* 🎯

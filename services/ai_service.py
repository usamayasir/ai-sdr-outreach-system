"""AI service using OpenAI-compatible API (Kimi, OpenAI, DeepSeek)."""
import json
import openai
from config.settings import get_settings


class AIService:
    """Handles all AI interactions: qualification, personalization, reply drafting, content generation."""

    def __init__(self):
        settings = get_settings()
        self.client = openai.AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url
        )
        self.model = settings.ai_model

    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000, json_mode: bool = False) -> str:
        """Generate text from the AI model."""
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # ── Qualification ──────────────────────────────────────────

    async def qualify_website(self, website_summary: str, chat_tools_found: list) -> dict:
        """Analyze website to determine if lead is qualified (no AI chat)."""
        prompt = f"""Analyze this business website and determine if they already have an AI chatbot or live chat solution.

Website Summary:
{website_summary}

Chat/Live tools detected: {chat_tools_found}

Respond ONLY in valid JSON with no markdown formatting:
{{
    "has_live_chat": true/false,
    "has_ai_chat": true/false,
    "chat_tools": ["tool1", "tool2"],
    "qualified": true/false,
    "reason": "brief 1-sentence explanation",
    "ai_score": 0-100  (higher = more likely to benefit from our AI chatbot)
}}

IMPORTANT: "qualified" should be TRUE only if they do NOT already have an AI chat solution. We target businesses that could benefit from adding AI chat."""
        raw = await self.generate(prompt, temperature=0.2, max_tokens=800, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "has_live_chat": False, "has_ai_chat": False, "chat_tools": [],
                "qualified": True, "reason": "Parse error — defaulting to qualified", "ai_score": 50.0
            }

    # ── Personalization ───────────────────────────────────────

    async def personalize_email(self, website_summary: str, business_type: str, pain_points: list) -> dict:
        """Generate personalized email sequence for a lead."""
        prompt = f"""Write a personalized cold email sequence for this business.

Website Summary:
{website_summary}

Business Type: {business_type}
Pain Points: {pain_points}

Create a complete outreach package:
1. Subject line (max 60 chars, compelling and personalized)
2. Personalized intro (1 sentence referencing their specific business)
3. Pain point hook (1 sentence about their industry challenge)
4. Benefits (2 bullet points, max 15 words each)
5. CTA (1 sentence, soft ask for a 10-minute call)
6. Full email body (max 120 words, natural and conversational)
7. LinkedIn message version (max 100 words, more casual)
8. WhatsApp message version (max 50 words, very short)

Respond ONLY in valid JSON:
{{
    "subject": "...",
    "intro": "...",
    "pain_point": "...",
    "benefits": "bullet 1\\nbullet 2",
    "cta": "...",
    "email_body": "...",
    "linkedin_message": "...",
    "whatsapp_message": "..."
}}"""
        raw = await self.generate(prompt, temperature=0.8, max_tokens=1500, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "subject": "Quick question about your business",
                "intro": "Hi, I came across your website and wanted to reach out.",
                "pain_point": "Many businesses in your industry struggle with customer engagement.",
                "benefits": "Increase response time by 80%\nCapture leads 24/7",
                "cta": "Would you be open to a quick 10-minute call this week?",
                "email_body": "Hi there, I came across your website and wanted to reach out. Many businesses in your industry struggle with customer engagement. Our AI chatbot can increase response time by 80% and capture leads 24/7. Would you be open to a quick 10-minute call this week?",
                "linkedin_message": "Hi! I came across your business and wanted to connect. We help companies like yours improve customer engagement with AI. Interested in a quick chat?",
                "whatsapp_message": "Hi! I help businesses improve customer engagement with AI chat. Quick 10-min chat this week?"
            }

    # ── Reply Classification ──────────────────────────────────

    async def categorize_reply(self, reply_text: str) -> str:
        """Classify an email reply into a category."""
        prompt = f"""Categorize this email reply into ONE of these categories:
- interested: prospect shows interest, wants to learn more, asks for pricing, requests a meeting
- question: prospect asks a question without clear commitment
- not_interested: prospect declines, says no, not interested, wrong timing
- spam: spam, auto-reply bounce, newsletter
- ooo: out of office, vacation auto-reply
- forwarded: email was forwarded to someone else

Reply text:
"""{reply_text}"""

Respond ONLY with the category name (one word, lowercase)."""
        result = await self.generate(prompt, temperature=0.2, max_tokens=50)
        return result.strip().lower().split()[0] if result.strip() else "question"

    async def analyze_sentiment(self, reply_text: str) -> float:
        """Return sentiment score from -1 (negative) to 1 (positive)."""
        prompt = f"""Rate the sentiment of this email reply on a scale from -1.0 (very negative) to 1.0 (very positive).

Reply:
"""{reply_text}"""

Respond ONLY with a single number between -1.0 and 1.0."""
        result = await self.generate(prompt, temperature=0.1, max_tokens=20)
        try:
            return float(result.strip())
        except (ValueError, TypeError):
            return 0.0

    # ── Reply Drafting ───────────────────────────────────────

    async def draft_reply(self, reply_text: str, category: str, email_history: str, business_info: str) -> str:
        """Draft a professional response to a prospect reply."""
        prompt = f"""Draft a professional, concise reply to this email.

Category: {category}
Business Info: {business_info}

Original reply from prospect:
"""{reply_text}"""

Email history:
"""{email_history}"""

Guidelines:
- If "not_interested": be polite, thank them, don't push. Mention they can reach out anytime.
- If "question": answer clearly and concisely. Add a soft CTA.
- If "interested": show enthusiasm, suggest specific meeting times (e.g., "Tuesday 2 PM or Thursday 10 AM"), ask for their preference.
- If "ooo": note when to follow up based on their return date.
- If "forwarded": thank them, ask for the best contact.
- Keep it under 150 words.
- Do NOT use overly salesy language. Be genuine and helpful."""
        return await self.generate(prompt, temperature=0.6, max_tokens=800)

    # ── Content Generation ───────────────────────────────────

    async def generate_content(self, content_type: str, topic: str, tone: str = "professional") -> str:
        """Generate marketing content (blog, LinkedIn, Facebook post)."""
        prompt = f"""Create a {content_type} post about: {topic}

Tone: {tone}

Requirements:
- Make it engaging and valuable
- Include a subtle call-to-action at the end
- Length appropriate for {content_type} (LinkedIn ~200 words, blog ~500 words, Facebook ~100 words)
- Use emojis sparingly (max 2-3) only if appropriate for the platform"""
        return await self.generate(prompt, temperature=0.8, max_tokens=2000)

    # ── Follow-up Generation ─────────────────────────────────

    async def generate_followup(self, email_history: str, followup_number: int, last_reply: str = None) -> dict:
        """Generate a follow-up email based on conversation history."""
        prompt = f"""Write follow-up email #{followup_number} for this cold outreach conversation.

Email history:
"""{email_history}"""

{f'Last reply from prospect: "{last_reply}"' if last_reply else ""}

Follow-up rules:
- Follow-up #1 (day 3): Gentle reminder, reference the original email, add a new value point
- Follow-up #2 (day 7): Mention a specific result or case study, create urgency
- Follow-up #3 (day 14): Final follow-up, ask for feedback or a referral

Respond ONLY in JSON:
{{
    "subject": "...",
    "body": "..."
}}"""
        raw = await self.generate(prompt, temperature=0.7, max_tokens=1000, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "subject": "Quick follow-up",
                "body": "Hi, just wanted to follow up on my previous email. Let me know if you'd like to chat!"
            }

"""Content Engine: Generate daily social media and blog content."""
from datetime import datetime, timezone, timedelta
from database.connection import async_session
from database.models import ContentPiece, ContentType
from services.ai_service import AIService


class ContentEngine:
    """Generate marketing content for LinkedIn, Facebook, and blog."""

    def __init__(self):
        self.ai = AIService()

    async def generate_daily_content(self) -> list:
        """Generate one piece of content for each platform."""
        topics = [
            "How AI chatbots are transforming customer service for small businesses",
            "5 signs your business needs an AI assistant",
            "Case study: How a dental clinic reduced response time by 80% with AI",
            "The ROI of AI chatbots: A data-driven breakdown",
            "Why 24/7 customer engagement matters more than ever",
        ]
        content_types = [ContentType.LINKEDIN, ContentType.FACEBOOK, ContentType.BLOG]

        created = []
        for content_type in content_types:
            topic = topics[hash(content_type.value + str(datetime.now().day)) % len(topics)]
            piece = await self.create_content(content_type, topic)
            if piece:
                created.append(piece)

        print(f"[ContentEngine] Generated {len(created)} content pieces")
        return created

    async def create_content(self, content_type: ContentType, topic: str) -> ContentPiece:
        """Generate a single content piece."""
        async with async_session() as session:
            tone_map = {
                ContentType.LINKEDIN: "professional, thought-leadership",
                ContentType.FACEBOOK: "friendly, conversational",
                ContentType.BLOG: "informative, educational",
                ContentType.WHATSAPP: "casual, direct"
            }
            tone = tone_map.get(content_type, "professional")

            content = await self.ai.generate_content(
                content_type=content_type.value,
                topic=topic,
                tone=tone
            )

            piece = ContentPiece(
                content_type=content_type,
                topic=topic,
                content=content,
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
                status="draft"
            )
            session.add(piece)
            await session.commit()
            await session.refresh(piece)
            print(f"[ContentEngine] ✓ Created {content_type.value} post: {topic[:40]}...")
            return piece

    async def get_scheduled_content(self) -> list:
        """Get content pieces scheduled for publishing."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(ContentPiece).where(
                    ContentPiece.status == "scheduled"
                )
            )
            return result.scalars().all()

    async def publish_content(self, piece_id: int) -> bool:
        """Mark content as published."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(ContentPiece).where(ContentPiece.id == piece_id))
            piece = result.scalar_one_or_none()
            if not piece:
                return False
            piece.status = "published"
            piece.published_at = datetime.now(timezone.utc)
            await session.commit()
            print(f"[ContentEngine] Published content {piece_id}")
            return True

    async def schedule_content(self, piece_id: int, scheduled_at: datetime) -> bool:
        """Schedule content for future publishing."""
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(ContentPiece).where(ContentPiece.id == piece_id))
            piece = result.scalar_one_or_none()
            if not piece:
                return False
            piece.scheduled_at = scheduled_at
            piece.status = "scheduled"
            await session.commit()
            return True

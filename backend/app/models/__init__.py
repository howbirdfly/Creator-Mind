"""Import ORM models here so Alembic can discover their metadata."""
from app.models.conversation import Conversation, Message

__all__ = ['Conversation', 'Message']

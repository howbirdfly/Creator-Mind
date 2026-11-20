"""CRUD endpoints for the MVP's local single-workspace conversations.

Authentication/tenant isolation is not implemented in the starter project;
add authorization before exposing these endpoints publicly.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageCreate,
    MessageOut,
)

router = APIRouter(prefix='/conversations', tags=['conversations'])


async def require_conversation(db: AsyncSession, conversation_id: UUID) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='对话不存在')
    return conversation


@router.get('', response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[Conversation]:
    result = await db.scalars(select(Conversation).order_by(Conversation.updated_at.desc(), Conversation.created_at.desc(), Conversation.id.desc()).limit(200))
    return list(result.all())


@router.post('', response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ConversationCreate, db: AsyncSession = Depends(get_db)) -> Conversation:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail='标题不能全为空格')
    conversation = Conversation(title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get('/{conversation_id}', response_model=ConversationOut)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)) -> Conversation:
    return await require_conversation(db, conversation_id)


@router.patch('/{conversation_id}', response_model=ConversationOut)
async def rename_conversation(conversation_id: UUID, payload: ConversationUpdate, db: AsyncSession = Depends(get_db)) -> Conversation:
    conversation = await require_conversation(db, conversation_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail='标题不能全为空格')
    conversation.title = title
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete('/{conversation_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    conversation = await require_conversation(db, conversation_id)
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/{conversation_id}/messages', response_model=list[MessageOut])
async def list_messages(conversation_id: UUID, db: AsyncSession = Depends(get_db)) -> list[Message]:
    await require_conversation(db, conversation_id)
    result = await db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc(), Message.id.asc()).limit(1000))
    return list(result.all())


@router.post('/{conversation_id}/messages', response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def create_message(conversation_id: UUID, payload: MessageCreate, db: AsyncSession = Depends(get_db)) -> Message:
    conversation = await require_conversation(db, conversation_id)
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail='消息不能为空')
    message = Message(conversation_id=conversation_id, role=payload.role, content=content)
    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(message)
    return message

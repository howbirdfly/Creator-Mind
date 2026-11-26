import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from app.api.routes import sources
from app.core.config import settings
from app.core.csrf import create_csrf
from app.core.security import generate_token, token_digest
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AuthSession, Conversation, Message, User
from app.services import source_storage

ORIGIN = "http://localhost:5173"


@pytest.fixture
async def resource_database():
    url = os.environ.get("CREATORMIND_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Resource authorization requires explicit CREATORMIND_TEST_DATABASE_URL")
    if not url.startswith("postgresql+asyncpg://"):
        pytest.fail("Resource authorization tests require PostgreSQL/asyncpg")
    schema = "auth_resources_" + uuid4().hex
    engine = create_async_engine(
        url,
        poolclass=NullPool,
        hide_parameters=True,
        connect_args={"server_settings": {"search_path": schema}},
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    created = False
    try:
        async with engine.begin() as conn:
            await conn.execute(CreateSchema(schema))
            created = True
            await conn.run_sync(Base.metadata.create_all)

        async def isolated_db() -> AsyncIterator:
            async with sessions() as db:
                yield db

        previous = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = isolated_db
        try:
            yield sessions
        finally:
            if previous is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous
    finally:
        if created:
            async with engine.begin() as conn:
                await conn.execute(DropSchema(schema, cascade=True))
        await engine.dispose()


async def seed_user(sessions, username: str):
    token = generate_token()
    async with sessions() as db, db.begin():
        user = User(username=username, password_hash="not-used-by-resource-tests")
        db.add(user)
        await db.flush()
        db.add(
            AuthSession(
                user_id=user.id,
                token_hash=token_digest(token),
                auth_version=1,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
    return user, token


def client_for(token: str) -> httpx.AsyncClient:
    csrf, _ = create_csrf(token)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost",
        cookies={settings.session_cookie_name: token, settings.csrf_cookie_name: csrf},
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )


async def test_materials_are_private_to_the_uploading_user(resource_database, monkeypatch) -> None:
    sessions = resource_database
    alice, alice_token = await seed_user(sessions, "alice")
    bob, bob_token = await seed_user(sessions, "bob")
    objects = {}
    payload = b"Private material"

    def put_object(source, file):
        objects[source.object_key] = file.read()

    monkeypatch.setattr(sources, "put_source_object", put_object)
    monkeypatch.setattr(source_storage, "_read_object", objects.__getitem__)
    async with client_for(alice_token) as a, client_for(bob_token) as b:
        path = "/api/v1/sources"
        files = {"file": ("notes.txt", payload, "text/plain")}
        rejected = await a.post(path, files=files, headers={"X-CSRF-Token": "invalid"})
        assert rejected.json()["code"] == "CSRF_INVALID"

        created = await a.post(path, files=files)
        assert created.status_code == 201
        assert created.headers["cache-control"] == "no-store"
        asset = created.json()
        assert (await a.get(path)).json() == [asset]
        assert (await a.get(f"{path}/count")).json() == {"total": 1}
        assert (await b.get(path)).json() == []
        assert (await b.get(f"{path}/count")).json() == {"total": 0}
        assert (await b.get(f"{path}/{asset['id']}")).status_code == 404

        async with sessions() as db:
            asset_id = UUID(asset["id"])
            result = await source_storage.read_source_file(db, asset_id, user_id=alice.id)
            assert result is not None
            assert result[1] == payload
            assert await source_storage.read_source_file(db, asset_id, user_id=bob.id) is None


async def test_all_resource_operations_enforce_owner(resource_database) -> None:
    sessions = resource_database
    alice, alice_token = await seed_user(sessions, "alice")
    _, bob_token = await seed_user(sessions, "bob")
    async with client_for(alice_token) as a, client_for(bob_token) as b:
        created = await a.post("/api/v1/conversations", json={"title": "Alice private"})
        assert created.status_code == 201
        conversation_id = created.json()["id"]
        path = f"/api/v1/conversations/{conversation_id}"
        saved = await a.post(path + "/messages", json={"content": "Private message"})
        assert saved.status_code == 201
        assert saved.json()["role"] == "user"
        assert (await a.get(path)).status_code == 200
        assert (await b.get("/api/v1/conversations")).json() == []
        for response in (
            await b.get(path),
            await b.patch(path, json={"title": "stolen"}),
            await b.delete(path),
            await b.get(path + "/messages"),
            await b.post(path + "/messages", json={"content": "intrusion"}),
        ):
            assert response.status_code == 404
            assert response.json()["code"] == "RESOURCE_NOT_FOUND"
        assert (await a.get(path + "/messages")).json()[0]["content"] == "Private message"
        assert (await a.patch(path, json={"title": "renamed"})).status_code == 200
        async with sessions() as db:
            stored = await db.get(Conversation, UUID(conversation_id))
            assert stored.user_id == alice.id
        assert (await a.delete(path)).status_code == 204
        async with sessions() as db:
            assert await db.get(Conversation, UUID(conversation_id)) is None
            assert (
                await db.scalar(
                    select(Message).where(Message.conversation_id == UUID(conversation_id))
                )
                is None
            )


async def test_public_writes_reject_spoofed_owner_and_message_roles(resource_database) -> None:
    sessions = resource_database
    _, token = await seed_user(sessions, "alice")
    bob, _ = await seed_user(sessions, "bob")
    async with client_for(token) as client:
        response = await client.post(
            "/api/v1/conversations", json={"title": "bad", "user_id": str(bob.id)}
        )
        assert response.status_code == 422
        conversation = (await client.post("/api/v1/conversations", json={})).json()
        path = f"/api/v1/conversations/{conversation['id']}"
        assert (
            await client.patch(path, json={"title": "bad", "user_id": str(bob.id)})
        ).status_code == 422
        for role in ("system", "assistant"):
            response = await client.post(path + "/messages", json={"role": role, "content": "fake"})
            assert response.status_code == 422
        assert (await client.get(path + "/messages")).json() == []

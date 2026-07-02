"""Chainlit UI for QualysGPT — streams agent responses over a session thread."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

import chainlit as cl

from agent import astream_events


@cl.on_chat_start
async def on_chat_start():
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)
    await cl.Message(content="QualysGPT ready. Ask me anything about your Qualys certifications.").send()


@cl.on_chat_resume
async def on_chat_resume(thread):
    session_id = thread.get("metadata", {}).get("session_id") or str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)


@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    config = {"configurable": {"thread_id": session_id}}

    msg = cl.Message(content="", author="QualysGPT")
    await msg.send()

    async for token in astream_events(message.content, session_id, config):
        await msg.stream_token(token)

    await msg.update()


@cl.set_chat_profiles
async def chat_profile():
    return None

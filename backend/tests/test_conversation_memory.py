"""Tests for ConversationMemory service."""

import os
import sys
import tempfile
import importlib.util
import pytest

# Load conversation_memory.py directly, bypassing services/__init__.py
# which pulls in heavyweight deps (lxml, docling, etc.)
_file = os.path.join(os.path.dirname(__file__), "..", "services", "conversation_memory.py")
_spec = importlib.util.spec_from_file_location("conversation_memory", _file)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ConversationMemory = _mod.ConversationMemory


@pytest.fixture
def memory(tmp_path):
    """Create a ConversationMemory that writes to a temp directory."""
    path = str(tmp_path / "context.md")
    return ConversationMemory(path=path)


class TestAddTurn:
    def test_single_turn(self, memory):
        memory.add_turn("What is AI?", "AI is artificial intelligence.")
        ctx = memory.get_context_for_prompt()
        assert "What is AI?" in ctx
        assert "AI is artificial intelligence." in ctx

    def test_multiple_turns(self, memory):
        memory.add_turn("Q1", "A1")
        memory.add_turn("Q2", "A2")
        ctx = memory.get_context_for_prompt()
        assert "Q1" in ctx
        assert "A2" in ctx

    def test_max_turns_trims_oldest(self):
        with tempfile.TemporaryDirectory() as td:
            m = ConversationMemory(path=os.path.join(td, "c.md"), max_turns=3)
            for i in range(5):
                m.add_turn(f"Q{i}", f"A{i}")
            ctx = m.get_context_for_prompt()
            # Only last 3 turns should remain
            assert "Q0" not in ctx
            assert "Q1" not in ctx
            assert "Q2" in ctx
            assert "Q4" in ctx


class TestGetContextForPrompt:
    def test_empty(self, memory):
        assert memory.get_context_for_prompt() == ""

    def test_format(self, memory):
        memory.add_turn("Hello", "Hi there")
        ctx = memory.get_context_for_prompt()
        assert "User: Hello" in ctx
        assert "Assistant: Hi there" in ctx

    def test_truncation(self, memory):
        memory.add_turn("Q", "A" * 10000)
        ctx = memory.get_context_for_prompt(max_chars=200)
        assert len(ctx) <= 200 + 50  # some overhead for prefix
        assert "earlier conversation omitted" in ctx


class TestClear:
    def test_clears_history(self, memory):
        memory.add_turn("Q", "A")
        memory.clear()
        assert memory.get_context_for_prompt() == ""

    def test_removes_file(self, memory):
        memory.add_turn("Q", "A")
        path = memory._path
        assert os.path.exists(path)
        memory.clear()
        assert not os.path.exists(path)


class TestFilePersistence:
    def test_writes_markdown_file(self, memory):
        memory.add_turn("Q1", "A1")
        with open(memory._path, encoding="utf-8") as f:
            content = f.read()
        assert "# Conversation Context" in content
        assert "**User:** Q1" in content
        assert "**Assistant:** A1" in content

    def test_overwrites_on_each_turn(self, memory):
        memory.add_turn("Q1", "A1")
        memory.add_turn("Q2", "A2")
        with open(memory._path, encoding="utf-8") as f:
            content = f.read()
        assert "Q1" in content
        assert "Q2" in content

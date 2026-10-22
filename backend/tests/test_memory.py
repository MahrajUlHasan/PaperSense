from services.memory import ConversationMemory


def test_sessions_are_separate_and_bounded():
    mem = ConversationMemory(max_turns=2)
    for i in range(3):
        mem.add_turn("ws-a", "chat-1", f"q{i}", f"a{i}")
    mem.add_turn("ws-a", "chat-2", "other", "x")
    history = mem.history("ws-a", "chat-1")
    assert "q0" not in history and "q2" in history
    assert "other" not in history
    mem.clear("ws-a", "chat-1")
    assert mem.history("ws-a", "chat-1") == ""

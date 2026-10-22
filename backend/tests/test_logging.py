from services.logging_setup import redact


def test_keys_are_redacted():
    line = "using AIzaSyA1234567890abcdefghijklmnop and gsk_abcdefghijklmnopqrstuvwx"
    out = redact(line)
    assert "AIza" not in out and "gsk_" not in out and out.count("[REDACTED]") == 2

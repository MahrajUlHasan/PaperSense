import pytest

from services.llm import ProviderError
from services.vision import VisionService


class FakeProvider:
    def __init__(self, failures, kind="unavailable"):
        self.failures, self.kind, self.calls = failures, kind, 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.failures:
            raise ProviderError("busy", kind=self.kind, provider="gemini")
        return '["a description"]'


def make_service(monkeypatch, provider):
    monkeypatch.setattr("services.vision.time.sleep", lambda s: None)
    monkeypatch.setattr("services.vision.vision_limiter.wait", lambda key: 0.0)
    service = VisionService("k" * 20)
    service._provider = provider
    return service


def test_busy_model_is_retried_patiently(monkeypatch):
    provider = FakeProvider(failures=2)
    assert make_service(monkeypatch, provider)._ask("p", [], 1) == ["a description"]
    assert provider.calls == 3


def test_gives_up_after_the_last_wait(monkeypatch):
    provider = FakeProvider(failures=5)
    with pytest.raises(ProviderError):
        make_service(monkeypatch, provider)._ask("p", [], 1)
    assert provider.calls == 3


def test_key_errors_are_not_retried(monkeypatch):
    provider = FakeProvider(failures=1, kind="invalid_key")
    with pytest.raises(ProviderError):
        make_service(monkeypatch, provider)._ask("p", [], 1)
    assert provider.calls == 1

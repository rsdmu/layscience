import os
from backend.server.services import summarizer


def test_summarise_uses_messages(monkeypatch):
    # ensure real API not called
    monkeypatch.delenv('DRY_RUN', raising=False)
    calls = {}

    class FakeResponses:
        def create(self, **kwargs):
            calls['kwargs'] = kwargs
            class R:
                output_text = 'ok'
            return R()

    class FakeClient:
        def __init__(self):
            self.responses = FakeResponses()

    monkeypatch.setattr(summarizer, 'OpenAI', FakeClient)

    summarizer.summarise('text', {}, 'default', system_prompt='sys')
    assert 'messages' in calls['kwargs']
    msgs = calls['kwargs']['messages']
    assert msgs[0]['role'] == 'system'
    assert msgs[0]['content'] == 'sys'

    monkeypatch.setenv('DRY_RUN', '1')

from app.core import llm


def test_detailed_summary_prompt_makes_core_concepts_deep(monkeypatch):
    captured = {}

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)

            class FakeChoice:
                class Message:
                    content = '{"title":"x","sections":[]}'

                message = Message()

            class FakeResponse:
                choices = [FakeChoice()]

            return FakeResponse()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm, "get_llm", lambda: FakeClient())

    llm._ask_detailed_summary_llm_sync("ctx", "topic", max_tokens=700)

    prompt = captured["messages"][0]["content"]
    assert "Core Concepts" in prompt
    assert "longest" in prompt.lower()
    assert "5 to 8" in prompt or "5-8" in prompt
    assert "2-4 sentences" in prompt or "2 to 4 sentences" in prompt


def test_basic_chat_prompt_encourages_synthesis_from_context(monkeypatch):
    captured = {}

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)

            class FakeChoice:
                class Message:
                    content = 'answer'

                message = Message()

            class FakeResponse:
                choices = [FakeChoice()]

            return FakeResponse()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm, "get_llm", lambda: FakeClient())

    llm._ask_llm_sync("chunk 1\n\nchunk 2", "tell me about the topic", max_tokens=800)

    prompt = captured["messages"][0]["content"]
    assert "synthesize" in prompt.lower() or "combine" in prompt.lower()
    assert "do not say you don't know" in prompt.lower() or "only say you don't know" in prompt.lower()
    assert "relevant" in prompt.lower()
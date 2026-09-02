from app.core import llm


def test_detailed_summary_prompt_makes_core_concepts_deep():
    prompt = llm._build_detailed_summary_prompt("ctx", "topic")

    assert "Core Concepts" in prompt
    assert "longest" in prompt.lower()
    assert "5 to 8" in prompt or "5-8" in prompt
    assert "2-4 sentences" in prompt or "2 to 4 sentences" in prompt


def test_basic_chat_prompt_encourages_synthesis_from_context():
    prompt = llm._build_chat_prompt("chunk 1\n\nchunk 2", "tell me about the topic")

    assert "synthesize" in prompt.lower() or "combine" in prompt.lower()
    assert "do not say you don't know" in prompt.lower() or "only say you don't know" in prompt.lower()
    assert "relevant" in prompt.lower()


def test_generate_text_falls_back_to_huggingface_when_gemini_fails(monkeypatch):
    captured = {}

    class FailingGeminiClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                raise RuntimeError("gemini unavailable")

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)

            class FakeChoice:
                class Message:
                    content = "fallback answer"

                message = Message()

            class FakeResponse:
                choices = [FakeChoice()]

            return FakeResponse()

    class FakeFallbackClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm, "get_gemini_client", lambda: FailingGeminiClient())
    monkeypatch.setattr(llm, "get_fallback_llm", lambda: FakeFallbackClient())

    result = llm._generate_text("some prompt", max_tokens=800, temperature=0.1)

    assert result == "fallback answer"
    assert captured["messages"][0]["content"] == "some prompt"


def test_generate_text_uses_gemini_when_available(monkeypatch):
    class FakeResponse:
        text = "gemini answer"

    class FakeGeminiClient:
        class models:
            @staticmethod
            def generate_content(**kwargs):
                return FakeResponse()

    monkeypatch.setattr(llm, "get_gemini_client", lambda: FakeGeminiClient())

    result = llm._generate_text("some prompt", max_tokens=800, temperature=0.1)

    assert result == "gemini answer"

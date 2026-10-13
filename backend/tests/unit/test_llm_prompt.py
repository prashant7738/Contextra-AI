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


def _fake_response(text="openai answer", prompt_tokens=1000, cached=200, completion=100):
    class Details:
        cached_tokens = cached

    class Usage:
        pass

    usage = Usage()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion
    usage.prompt_tokens_details = Details()

    class Message:
        content = text

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    response = Response()
    response.usage = usage
    return response


def _fake_client(create):
    class Completions:
        pass

    Completions.create = staticmethod(create)

    class Client:
        chat = type("Chat", (), {"completions": Completions()})()

    return Client()


def test_generate_text_uses_gpt_6_luna_and_settles_real_usage(monkeypatch):
    captured = {}
    ledger = {}

    def create(**kwargs):
        captured.update(kwargs)
        return _fake_response()

    monkeypatch.setattr(llm, "get_openai_client", lambda: _fake_client(create))
    monkeypatch.setattr(llm.budget, "reserve", lambda micro: ledger.setdefault("reserved", micro))
    monkeypatch.setattr(llm.budget, "settle", lambda reserved, actual: ledger.update(settled=(reserved, actual)))
    monkeypatch.setattr(llm, "_unsupported_params", set())

    result = llm._generate_text("some prompt", max_tokens=800, temperature=0.1)

    assert result == "openai answer"
    assert captured["model"] == "gpt-6-luna"
    assert captured["messages"][0]["content"] == "some prompt"
    assert captured["max_completion_tokens"] == 800
    # 800 uncached input + 200 cached input + 100 output, at 0.10 / 0.01 / 0.50 per 1M
    reserved, actual = ledger["settled"]
    assert actual == 80 + 2 + 50
    assert actual < reserved


def test_generate_text_drops_params_the_model_rejects(monkeypatch):
    import httpx
    import openai

    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if "temperature" in kwargs:
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx.Response(400, request=request)
            raise openai.BadRequestError("Unsupported value: 'temperature'", response=response, body=None)
        return _fake_response()

    monkeypatch.setattr(llm, "get_openai_client", lambda: _fake_client(create))
    monkeypatch.setattr(llm.budget, "reserve", lambda micro: micro)
    monkeypatch.setattr(llm.budget, "settle", lambda reserved, actual: None)
    monkeypatch.setattr(llm, "_unsupported_params", set())

    assert llm._generate_text("p", max_tokens=100, temperature=0.2) == "openai answer"
    assert "temperature" in calls[0]
    assert "temperature" not in calls[1]


def test_generate_text_refunds_reservation_when_request_was_rejected(monkeypatch):
    import httpx
    import openai
    import pytest

    ledger = {}

    def create(**kwargs):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        raise openai.AuthenticationError("bad key", response=httpx.Response(401, request=request), body=None)

    monkeypatch.setattr(llm, "get_openai_client", lambda: _fake_client(create))
    monkeypatch.setattr(llm.budget, "reserve", lambda micro: micro)
    monkeypatch.setattr(llm.budget, "settle", lambda reserved, actual: ledger.update(settled=(reserved, actual)))
    monkeypatch.setattr(llm, "_unsupported_params", set())

    with pytest.raises(openai.AuthenticationError):
        llm._generate_text("p", max_tokens=100, temperature=0.2)

    assert ledger["settled"][1] == 0

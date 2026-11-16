import json
from unittest.mock import Mock

import pytest

from app.modules.headlines.impact import ImpactRequest, RAIL_URL, analyze, impact


def query(tickers=(), holdings=(), **changes):
    args = {"headline": {"title": "Headline", "url": RAIL_URL, "tickers": tickers, "published": "2026-04-01"},
            "holdings": [{"ticker": ticker, "quantity": qty} for ticker, qty in holdings]}
    return ImpactRequest.model_validate({**args, **changes})


def test_replay_uses_its_own_positions_and_date():
    august = impact(query(replay="august"))
    assert "10%" in august["links"][0]["text"]
    assert august["update"] is None
    assert "5.8 million" in impact(query(replay="november"))["update"]["text"]
    empty = impact(query(holdings=[("CHE.UN", 3)], replay="november", include_chemtrade=False))
    assert not empty["links"] and not empty["question"] and not empty["update"]


def test_live_uses_tagged_positions_and_dated_relationships():
    result = impact(query(["AAPL"], [("AAPL", 1), ("AVGO", 2)]))
    assert result["direct"] == ["AAPL"]
    assert [link["ticker"] for link in result["links"]] == ["AVGO"]
    assert not impact(query(["AAPL"], [("AVGO", None)]))["question"]
    request = query(["AAPL"], [("AVGO", 2)])
    request.headline.published = None
    assert not impact(request)["links"]
    assert not impact(query(["AAPL", "AVGO"], [("AVGO", 2)]))["links"]
    assert impact(query(["BRK-B"], [("BRK.B", 2)]))["direct"] == ["BRK.B"]


@pytest.mark.parametrize(("quantity", "held", "tracked"), [
    (None, [], ["TTWO"]), (2, ["TTWO"], []),
])
def test_gta_headline_matches_take_two_with_or_without_share_count(quantity, held, tracked):
    request = query(["TTWO"], [("TTWO", quantity), ("INTC", None)])
    request.headline.title = "The Grand Theft Auto 6 economy reaches far and wide"
    result = impact(request)
    assert result["direct"] == held
    assert result["watchlist"] == tracked
    assert result["question"]


def model_reply(connections):
    client = Mock()
    client.converse.return_value = {"stopReason": "tool_use", "output": {"message": {"content": [{
        "toolUse": {"name": "explain_impact", "input": {"connections": connections, "question": "What next?"}}
    }]}}}
    return client


@pytest.mark.parametrize("coverage", ["excerpt", "full", "unknown", "missing"])
def test_model_receives_article_portfolio_and_coverage_without_requiring_tags(coverage):
    request = query([], [("TTWO", 3), ("AAPL", None)])
    request.headline.content = "" if coverage == "missing" else "GTA is published by Take-Two."
    request.headline.source_content_type = coverage
    request.headline.summary = "Feed summary."
    request.holdings[0].name = "Take-Two"
    item = {"ticker": "TTWO", "evidence_id": 1,
            "explanation": "The launch matters to the publisher."}
    client = model_reply([item])
    result = analyze(request, impact(request), "model", client)
    payload = json.loads(client.converse.call_args.kwargs["messages"][0]["content"][0]["text"])
    assert payload["article"]["source_content_type"] == coverage
    assert payload["passages"][1]["text"] == (request.headline.content or request.headline.summary)
    assert payload["portfolio"][0] == {"ticker": "TTWO", "quantity": 3, "name": "Take-Two"}
    assert payload["portfolio"][1]["quantity"] is None
    expected_source = "feed_summary" if coverage == "missing" else "article"
    assert result["connections"] == [{"ticker": "TTWO", "explanation": item["explanation"],
                                      "quote": request.headline.content or request.headline.summary,
                                      "quote_source": expected_source}] and result["question"]


@pytest.mark.parametrize(("ticker", "evidence_id"), [
    ("OTHER", 0), ("TTWO", 99), ("TTWO", 1),
])
def test_unverified_model_output_is_rejected(ticker, evidence_id):
    request = query(["AAPL"], [("TTWO", 2), ("AVGO", 1)])
    client = model_reply([{"ticker": ticker, "evidence_id": evidence_id, "explanation": "Claim."}])
    with pytest.raises(ValueError):
        analyze(request, impact(request), "model", client)


def test_no_supported_connection_is_a_valid_result():
    request = query(["AAPL"], [("AVGO", 1)])
    result = analyze(request, impact(request), "model", model_reply([]))
    assert result["links"] == [] and result["connections"] == [] and result["question"] is None


def test_incomplete_model_answer_is_retryable():
    client = model_reply([])
    client.converse.return_value["stopReason"] = "max_tokens"
    request = query()
    with pytest.raises(ValueError):
        analyze(request, impact(request), "model", client)

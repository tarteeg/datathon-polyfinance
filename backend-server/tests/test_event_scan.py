from types import SimpleNamespace

from app.modules.riskripple.event_routes import Request
from app.riskripple import event_scan as agent


def test_untagged_event_outranks_routine_coverage(monkeypatch):
    feed = {"start": "2026-10-16", "end": "2026-11-15", "events": [], "companies": []}
    for ticker, name in [("CHIP", "Chipmaker"), ("UNRL", "Grocer"), ("FDRY", "Foundry Company")]:
        feed["companies"].append({"ticker": ticker, "name": name})
    for index, title in enumerate(["New chip export restrictions enacted", "Grocer opens a store"]):
        feed["events"].append({"id": str(index), "version": 1, "published": "2026-11-10",
                               "title": title, "urls": [str(index)], "tickers": [] if not index else ["UNRL"]})
    monkeypatch.setattr(agent, "fetch_recent_events", lambda: feed)
    monkeypatch.setattr(agent, "position_weights", lambda holdings: {"CHIP": .75, "UNRL": .25})
    monkeypatch.setattr(agent, "fetch_article_by_url", lambda url: {"article": {"title": feed["events"][int(url)]["title"]}})
    passages = {"CHIP": "We sell restricted processors to the affected destination.",
                "FDRY": "Our foundry manufactures those processors under volume contracts."}

    def index(s):
        hit = SimpleNamespace(chunk=SimpleNamespace(text=passages.get(s, "We sell groceries.")))
        return SimpleNamespace(retrieve=lambda *a, **kw: [hit]), {"source_url": "https://issuer.example/" + s,
                                                                  "publication_date": "2026-02-01"}
    monkeypatch.setattr(agent, "filing_index", index)

    def ask(_model, schema, _instructions, data):
        if schema is agent.Screen:
            return schema(candidates=[{"event": i, "significance": 5-i, "search_terms": "processor",
                                       "outside": ["FDRY", "FAKE", "CHIP"]} for i in range(2)])
        sources = data["evidence"]
        title = sources[0]["headline"]
        ticks = ["CHIP", "FDRY"] if title.startswith("New") else ["UNRL"]
        findings = []
        for s in ticks:
            cites = [{"source": 0, "quote": title}]
            if s in passages:
                cites.append({"source": next(i for i, src in enumerate(sources) if src.get("ticker") == s),
                              "quote": passages[s]})
            findings.append({"ticker": s, "relationship": "indirect" if s in passages else "direct",
                             "significance": 5 if s in passages else 1, "direction": "potential pressure",
                             "explanation": "Orders could decline if customers cut purchases.", "citations": cites})
        return schema(findings=findings)

    monkeypatch.setattr(agent, "ask", ask)
    result = agent.scan({"CHIP": 3, "UNRL": 1, "WATCH": None}, "test")
    first, second = result["events"]
    assert (first["id"], second["id"]) == ("0", "1")
    assert first["exposed_weight"] == .75
    assert [h["status"] for h in first["holdings"]] == ["supported", "no supported connection", "no supported connection"]
    assert first["holdings"][2]["watchlist"]
    assert [item["ticker"] for item in first["outside"]] == ["FDRY"]
    assert result["screened"] == 2 and result["warnings"] == []


def test_citations_must_support_company_and_resolve_verbatim():
    sources = [{"kind": "article", "text": "A tariff was imposed on imported cars."},
               {"kind": "filing", "text": "This company imports those cars.", "ticker": "OTHER"}]
    citations = [agent.Citation(source=i, quote=s["text"]) for i, s in enumerate(sources)]
    item = agent.Finding(ticker="AUTO", relationship="indirect", direction="mixed", significance=4,
                         explanation="Costs could rise for this importer.", citations=citations)
    def validate():
        return agent.verified_findings(agent.Assessment(findings=[item]), sources, {"AUTO": "Automaker"})
    assert not validate()
    sources[1]["ticker"] = "AUTO"
    assert validate()["AUTO"]["citations"][1]["quote"] == sources[1]["text"]
    item.relationship = "direct"
    assert not validate()
    item.relationship = "indirect"
    item.citations[0].quote = "The publisher did not write this."
    assert not validate()


def test_latest_portfolio_snapshot_key():
    original = Request(user_id="owner", holdings={"A": 1, "B": None})
    assert original.cache_type() == Request(user_id="owner", holdings={"B": None, "A": 1}).cache_type()
    assert original.cache_type() != Request(user_id="owner", holdings={"A": 2, "B": None}).cache_type()


def test_incomplete_screening_cannot_return_successful_empty_scan(monkeypatch):
    event = {"title": "Example", "published": "2026-11-10"}
    monkeypatch.setattr(agent, "fetch_recent_events", lambda: {"events": [event], "companies": [],
                        "start": "2026-10-16", "end": "2026-11-15"})
    monkeypatch.setattr(agent, "filing_index", lambda _: None)
    monkeypatch.setattr(agent, "ask", lambda *_: 1 / 0)
    import pytest
    with pytest.raises(RuntimeError, match="screen"):
        agent.scan({"A": None}, "test")


def test_weights_require_every_owned_quote_in_one_currency(monkeypatch):
    prices = {"US": SimpleNamespace(price=20, currency="USD"), "CA": SimpleNamespace(price=10, currency="CAD")}
    monkeypatch.setattr(agent, "fetch_current_prices", lambda symbols: {s: prices[s] for s in symbols})
    portfolio = {"US": 1, "CA": 2, "WATCH": None}
    assert agent.position_weights(portfolio) == {}
    prices["CA"].currency = "USD"
    assert agent.position_weights(portfolio) == {"US": .5, "CA": .5}
    prices["US"].price = None
    assert agent.position_weights(portfolio) == {}


def test_full_month_compared_before_source_lookup(monkeypatch):
    events = [{"title": f"Event {i}", "id": str(i), "published": "2026-11-05"} for i in range(301)]
    feed = {"events": events, "companies": [{"ticker": "A"}], "start": "2026-10-16", "end": "2026-11-15"}
    monkeypatch.setattr(agent, "fetch_recent_events", lambda: feed)
    visited = []
    def ask(_model, schema, _prompt, data):
        if schema is agent.Screen:
            return schema(candidates=[{"event": row[0], "significance": 3, "search_terms": "input costs", "outside": []}
                                      for row in data["events"][:5]])
        assert schema is agent.Priorities
        assert {0, 100, 200, 300}.issubset(x["id"] for x in data["candidates"])
        return schema(events=[300])
    monkeypatch.setattr(agent, "ask", ask)
    def unavailable(event):
        visited.append(event["id"])
        return [], True
    monkeypatch.setattr(agent, "publisher_passages", unavailable)
    result = agent.scan({"A": None}, "test")
    assert result["screened"] == 301 and result["shortlisted"] == 1 and visited == ["300"]
    assert result["warnings"] and not result["events"]


def test_same_findings_get_a_separate_investor_interpretation(monkeypatch):
    from copy import deepcopy
    from app.riskripple.personas.profiles import PersonaId

    finding = {"ticker": "PEP", "status": "supported", "weight": .10, "explanation": "The company announced job cuts."}
    base = [{"id": "one", "title": "PepsiCo announces restructuring", "holdings": [finding]}]
    prompts = []
    def review(model, schema, prompt, data):
        prompts.append(prompt)
        assert data["events"][0]["holdings"] == [finding]
        return schema(notes=[{"event_id": "one", "ticker": "PEP", "interpretation": "This is a question of execution.",
                              "question": "Which filing will disclose restructuring costs?"}])
    monkeypatch.setattr(agent, "ask", review)
    for persona in PersonaId:
        events = deepcopy(base)
        assert agent.add_investor_notes(events, "model", persona)
        assert events[0].pop("investor_note")["ticker"] == "PEP"
        assert events == base
    assert "diversification" in prompts[0] and "15+" in prompts[0]
    assert "governance" in prompts[1] and "8-12" in prompts[1]
    assert "income reliability" in prompts[2] and "3-5" in prompts[2]


def test_unverified_persona_note_cannot_create_a_position(monkeypatch):
    from app.riskripple.personas.profiles import PersonaId
    events = [{"id": "one", "title": "Restructuring", "holdings": [{"ticker": "A", "status": "incomplete"}]}]
    monkeypatch.setattr(agent, "ask", lambda *args: agent.InvestorReview(notes=[{
        "event_id": "one", "ticker": "A", "interpretation": "This would be unsupported.",
        "question": "Can this unsupported position explain the event?"}]))
    assert not agent.add_investor_notes(events, "model", PersonaId.MATEO)
    assert "investor_note" not in events[0]


def test_profile_switch_isolates_saved_reports_and_keeps_neutral_key():
    import hashlib
    import json
    args = {"user_id": "owner", "holdings": {"PEP": 1}}
    neutral = Request(**args)
    old_key = "events30:" + hashlib.sha256(json.dumps(neutral.holdings, sort_keys=True).encode()).hexdigest()
    assert neutral.cache_type() == old_key
    assert len({neutral.cache_type(), *(Request(**args, persona=p).cache_type() for p in ("amira","mateo","robert"))}) == 4

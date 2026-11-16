from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.riskripple import event_scan as agent
from app.riskripple.personas.profiles import PersonaId
from app.riskripple.scan_run import ScanCache, ScanRun, digest


@pytest.fixture
def scenario(monkeypatch):
    cache = ScanCache()
    feed = {"start": "2026-10-16", "end": "2026-11-15", "companies": [{"ticker": "EX", "name": "Example"}],
            "events": [{"id": day, "version": 1, "published": "2026-11-" + day, "title": "Example opens a factory " + day,
                        "urls": [day]} for day in ("04", "02")]}
    bodies = {}
    stamps = {"EX": [[1, 1], [1, 1]]}
    prompts = []
    snapshots = []
    monkeypatch.setattr(agent, "filing_stamp", lambda s: deepcopy(stamps.get(s)))
    monkeypatch.setattr(agent, "filing_index", lambda _: (SimpleNamespace(retrieve=lambda *a, **kw: []),
                                                           {"publication_date": "2025-01-01"}))
    monkeypatch.setattr(agent, "position_weights", lambda h: {"EX": 1})
    monkeypatch.setattr(agent, "fetch_article_by_url", lambda url: {"article": {
        "title": "Example opens a factory " + url, "content": bodies.get(url, "")}})

    def ask(model, schema, prompt, data):
        prompts.append(schema)
        if schema is agent.Screen:
            return schema(candidates=[{"event": row[0], "significance": 3, "search_terms": "factory", "outside": []}
                                      for row in data["events"]])
        if schema is agent.InvestorReview:
            return schema(notes=[{"event_id": event["event_id"], "ticker": "EX", "interpretation": "Capacity may grow.",
                                  "question": "How much demand is contracted?"} for event in data["events"]])
        source = data["evidence"][0]
        return schema(findings=[{"ticker": "EX", "relationship": "direct", "significance": 3, "direction": "mixed",
                                 "explanation": "Capacity may rise if orders materialize.",
                                 "citations": [{"source": 0, "quote": source["headline"]}]}])

    monkeypatch.setattr(agent, "ask", ask)

    def scan(persona=None, quantity=1):
        prompts.clear()
        snapshots.clear()
        run = ScanRun(cache, lambda activity: snapshots.append(deepcopy(activity)))
        result = agent.scan({"EX": quantity}, "model", persona, run=run, feed=feed)
        assert run.activity["model_calls"] == len(prompts)
        return result
    return SimpleNamespace(**locals())


def test_repeat_and_persona_switch_reuse_verified_evidence(scenario):
    s = scenario
    first = s.scan(PersonaId.AMIRA)
    assert s.prompts.count(agent.Screen) == s.prompts.count(agent.Assessment) == 2
    assert s.prompts.count(agent.InvestorReview) == 1
    early = next(activity for activity in s.snapshots if activity["partial"])
    assert early["partial"][0]["holdings"][0]["citations"] and early["first_finding_ms"] is not None
    assert all(step["key"] != "rank" for step in early["steps"])
    assert s.scan(PersonaId.AMIRA) == first and not s.prompts
    assert s.scan(PersonaId.ROBERT)["persona"] == "robert" and s.prompts == [agent.InvestorReview]
    assert "investor_note" not in s.scan()["events"][0] and not s.prompts


def test_incremental_revision_addition_expiry_and_position_edits(scenario):
    s = scenario
    s.scan()
    s.feed["events"][1]["version"] += 1
    s.scan()
    assert s.prompts == [agent.Screen, agent.Assessment]
    added = dict(s.feed["events"][0], id="06", published="2026-11-06", urls=["06"])
    s.feed["events"].insert(0, added)
    assert len(s.scan()["events"]) == 3
    assert s.prompts == [agent.Screen, agent.Assessment]
    s.feed["events"].pop()
    assert {e["id"] for e in s.scan()["events"]} == {"04", "06"} and not s.prompts
    assert len(s.scan(quantity=2)["events"]) == 2 and not s.prompts


def test_body_recheck_and_filing_revision(scenario):
    s = scenario
    s.scan()
    s.stamps["EX"][0][0] += 1
    assert agent.current_research({"EX": 1}, "model", s.feed, ScanRun(s.cache)) is None
    s.bodies["04"] = "Updated order volumes."
    s.cache.entries.pop(digest("articles", s.feed["events"][0]))
    s.scan()
    assert s.prompts == [agent.Assessment]


def test_retries_incomplete_evidence_and_missing_persona_notes(scenario, monkeypatch):
    s = scenario
    original = agent.publisher_passages
    monkeypatch.setattr(agent, "publisher_passages", lambda _: ([], True))
    assert s.scan()["warnings"]
    assert not s.cache.get(agent.research_key({"EX": 1}, "model"))
    monkeypatch.setattr(agent, "publisher_passages", original)
    original_ask = agent.ask
    def no_notes(model, schema, prompt, data):
        if schema is agent.InvestorReview:
            s.prompts.append(schema)
            return schema(notes=[])
        return original_ask(model, schema, prompt, data)
    monkeypatch.setattr(agent, "ask", no_notes)
    assert s.scan(PersonaId.MATEO)["warnings"]
    monkeypatch.setattr(agent, "ask", original_ask)
    assert not s.scan(PersonaId.MATEO)["warnings"] and s.prompts == [agent.InvestorReview]


def test_changed_weights_rerank_without_rescreening_or_reassessing(scenario, monkeypatch):
    s = scenario
    holdings = {"EX": 1, "NEXT": 1}
    weights = {"EX": .9, "NEXT": .1}
    s.feed["companies"].append({"ticker": "NEXT", "name": "Next Company"})
    monkeypatch.setattr(agent, "position_weights", lambda _: dict(weights))
    monkeypatch.setattr(agent, "fetch_article_by_url", lambda url: {"article": {
        "title": ("EX" if url == "04" else "NEXT") + " announces new orders"}})
    model = agent.ask
    def ask(model_id, schema, prompt, data):
        if schema is not agent.Assessment:
            return model(model_id, schema, prompt, data)
        s.prompts.append(schema)
        headline = data["evidence"][0]["headline"]
        return schema(findings=[{"ticker": headline.split()[0], "relationship": "direct", "significance": 3,
                                 "direction": "mixed", "explanation": "Orders affect future sales.",
                                 "citations": [{"source": 0, "quote": headline}]}])
    monkeypatch.setattr(agent, "ask", ask)
    def ranked():
        return [e["id"] for e in agent.scan(holdings, "model", feed=s.feed, run=ScanRun(s.cache))["events"]]
    assert ranked() == ["04", "02"]
    for key in (agent.research_key(holdings, "model"), digest("weights", holdings)):
        s.cache.entries.pop(key)
    weights.update(EX=.1, NEXT=.9)
    s.prompts.clear()
    assert ranked() == ["02", "04"] and not s.prompts

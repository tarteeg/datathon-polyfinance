"""Trickle-down investigation routes: sanctions/regulatory/macro data ingestion reads,
plus the Ripple Investigation Agent (Bedrock/Strands) tying them together with the
company exposure graph and RAG retrieval over filings.

Ported from riskripple-ai (see app/riskripple/). Finance (deterministic portfolio math)
and persona (Amira/Mateo/Robert) tooling were ported in a later pass -- see
app/riskripple/finance/ and app/riskripple/personas/.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.riskripple.alerts import db as alerts_db
from app.riskripple.alerts.db import get_all_portfolios
from app.riskripple.alerts.pipeline import run_alert_scan
from app.riskripple.briefing import build_event_briefing, persona_attention_level
from app.riskripple.finance.live_portfolio import (
    compute_annualized_volatility,
    compute_real_weights,
    fetch_daily_price_history,
)
from app.riskripple.finance.returns import align_price_panel, daily_returns, returns_panel
from app.riskripple.finance.risk import correlation_matrix, max_drawdown
from app.riskripple.finance.stress import TIER_SHOCKS, build_tier_shock_scenario, run_stress_test
from app.riskripple.ingestion import macro_fred, news_stocksfeed, regulatory_events, sanctions_gac, sanctions_ofac
from app.riskripple.personas.assessment import compare_personas
from app.riskripple.tools.research_tools import extract_candidate_entities

router = APIRouter(prefix="/riskripple", tags=["riskripple"])


def _dataclass_list(items) -> list[dict]:
    return [asdict(i) if is_dataclass(i) else i for i in items]


def _metadata_dict(metadata) -> dict:
    if hasattr(metadata, "model_dump"):
        return metadata.model_dump(mode="json")
    return asdict(metadata)


@router.get("/sanctions/ofac")
def get_ofac_sanctions(search: str | None = None, limit: int = Query(50, ge=1, le=500)):
    """Live OFAC Specially Designated Nationals list. `search` filters by substring
    match on sdn_name (case-insensitive); otherwise returns the first `limit` records."""
    try:
        result = sanctions_ofac.fetch_sdn_list()
    except Exception as exc:
        raise HTTPException(502, f"OFAC fetch failed: {exc}") from exc

    records = result.records
    if search:
        needle = search.lower()
        records = [r for r in records if needle in (r.sdn_name or "").lower()]
    return {
        "metadata": _metadata_dict(result.metadata),
        "total_records": len(result.records),
        "returned": min(limit, len(records)),
        "records": _dataclass_list(records[:limit]),
    }


@router.get("/sanctions/gac")
def get_gac_sanctions(search: str | None = None, limit: int = Query(50, ge=1, le=500)):
    """Live Global Affairs Canada consolidated autonomous sanctions list."""
    try:
        result = sanctions_gac.fetch_consolidated_list()
    except Exception as exc:
        raise HTTPException(502, f"GAC fetch failed: {exc}") from exc

    records = result.records
    if search:
        needle = search.lower()
        records = [
            r for r in records
            if needle in ((r.entity_name or "") + (r.last_name or "") + (r.given_name or "")).lower()
        ]
    return {
        "metadata": _metadata_dict(result.metadata),
        "total_records": len(result.records),
        "returned": min(limit, len(records)),
        "records": _dataclass_list(records[:limit]),
    }


@router.get("/regulatory/events")
def get_regulatory_events(term: str | None = None, per_page: int = Query(20, ge=1, le=100)):
    """Live Federal Register search. Omit `term` to use the broad default net
    (semiconductor export, export administration regulations, entity list addition,
    critical minerals, rare earth)."""
    try:
        if term:
            result = regulatory_events.search_documents(term=term, per_page=per_page)
        else:
            result = regulatory_events.search_documents_multi(per_page=per_page)
    except Exception as exc:
        raise HTTPException(502, f"Federal Register fetch failed: {exc}") from exc

    return {
        "metadata": _metadata_dict(result.metadata),
        "count": len(result.documents),
        "documents": _dataclass_list(result.documents),
    }


@router.get("/macro/{series_id}")
def get_macro_series(series_id: str):
    """Live FRED series (e.g. DGS10, DGS3MO, DFF, CPIAUCSL)."""
    try:
        result = macro_fred.fetch_series(series_id)
    except Exception as exc:
        raise HTTPException(502, f"FRED fetch failed for {series_id}: {exc}") from exc

    observations = [
        {"date": idx.date().isoformat(), "value": float(val)}
        for idx, val in result.observations.items()
    ]
    return {
        "series_id": result.series_id,
        "metadata": _metadata_dict(result.metadata),
        "count": len(observations),
        "observations": observations,
    }


class InvestigateRequest(BaseModel):
    event_description: str
    portfolio_holdings: list[str]
    # Optional real share quantities (symbol -> shares). When given, portfolio_impact
    # and persona_comparison are computed from real, live-priced position weights
    # instead of an assumed equal weighting -- see _extract_structured_findings and
    # _build_portfolio_and_persona_sections below.
    portfolio_quantities: dict[str, float] | None = None
    # When given, a successful investigation is persisted to
    # riskripple_investigation_history so it can be revisited later (the
    # Investigations page's "previously completed manual investigations" tier).
    user_id: str | None = None


def _extract_structured_findings(messages: list[dict]) -> tuple[dict[str, dict], dict | None, dict[str, str]]:
    """Scan the agent's real tool-call trace (not its free-text prose) for the
    structured decisions it recorded via record_exposure_classification and
    record_followup_finding, plus the real per-holding SEC industry classification
    from its load_company_graph call. Returns (exposure_classifications keyed by
    symbol, followup_finding or None, industries keyed by symbol).
    """
    exposure: dict[str, dict] = {}
    followup: dict | None = None
    industries: dict[str, str] = {}

    for message in messages:
        for block in message.get("content", []) or []:
            if not isinstance(block, dict):
                continue
            tool_use = block.get("toolUse")
            if tool_use and tool_use.get("name") == "record_exposure_classification":
                inp = tool_use.get("input") or {}
                symbol = inp.get("symbol")
                if symbol and inp.get("tier") in TIER_SHOCKS:
                    exposure[symbol] = {"tier": inp["tier"], "reason": inp.get("reason", "")}
            elif tool_use and tool_use.get("name") == "record_followup_finding":
                followup = tool_use.get("input") or {}
            elif tool_use and tool_use.get("name") == "load_company_graph":
                pass  # industries come from the RESULT, not the call -- handled below

            tool_result = block.get("toolResult")
            if tool_result:
                content = tool_result.get("content") or []
                for c in content:
                    text = c.get("text") if isinstance(c, dict) else None
                    if not text:
                        continue
                    try:
                        parsed = json.loads(text)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(parsed, dict) and "industries" in parsed and isinstance(parsed["industries"], dict):
                        for symbol, sic in parsed["industries"].items():
                            if sic:
                                industries[symbol] = sic

    return exposure, followup, industries


def _build_correlation_and_drawdown(portfolio_holdings: list[str]) -> tuple[dict | str, dict[str, dict | str]]:
    """Real, deterministic correlation matrix and per-holding max-drawdown, computed
    from the same real daily price history already fetched for volatility -- not a
    second, duplicate fetch path, and never an LLM-generated number. Degrades
    explicitly (a string message, not a silent omission or a whole-response failure)
    when there isn't enough real data to compute one of these: a single holding has no
    pairwise correlation to show, and a symbol with too little price history can't
    support a drawdown estimate.
    """
    prices: dict[str, object] = {}
    for symbol in portfolio_holdings:
        series = fetch_daily_price_history(symbol)
        if series is not None and len(series) >= 20:
            prices[symbol] = series

    drawdowns: dict[str, dict | str] = {}
    for symbol in portfolio_holdings:
        series = prices.get(symbol)
        if series is None:
            drawdowns[symbol] = "Not enough real price history to compute a drawdown estimate."
            continue
        try:
            result = max_drawdown(daily_returns(series))
            drawdowns[symbol] = {
                "max_drawdown_pct": result.max_drawdown,
                "peak_date": result.peak_date.date().isoformat(),
                "trough_date": result.trough_date.date().isoformat(),
                "recovery_date": result.recovery_date.date().isoformat() if result.recovery_date is not None else None,
            }
        except Exception as exc:  # noqa: BLE001 -- drawdown is supporting context, never fatal
            drawdowns[symbol] = f"Could not compute: {type(exc).__name__}: {exc}"

    if len(prices) < 2:
        correlation: dict | str = (
            "Correlation requires at least 2 holdings with sufficient real price history; "
            f"only {len(prices)} of {len(portfolio_holdings)} qualified."
        )
    else:
        try:
            panel = align_price_panel(prices)
            corr_df = correlation_matrix(returns_panel(panel))
            correlation = {row: corr_df.loc[row].to_dict() for row in corr_df.index}
        except Exception as exc:  # noqa: BLE001 -- correlation is supporting context, never fatal
            correlation = f"Could not compute: {type(exc).__name__}: {exc}"

    return correlation, drawdowns


def _build_portfolio_and_persona_sections(
    portfolio_holdings: list[str],
    portfolio_quantities: dict[str, float] | None,
    exposure_classifications: dict[str, dict],
    industries: dict[str, str],
) -> tuple[dict, dict, dict[str, str], dict[str, float]]:
    """Deterministic (non-LLM) portfolio-impact and persona-comparison sections, built
    from the agent's own recorded exposure tiers -- never an LLM-generated number."""
    tiers = {
        symbol: exposure_classifications.get(symbol, {}).get("tier", "no_established_link")
        for symbol in portfolio_holdings
    }

    weights_are_real = False
    price_errors: dict[str, str] = {}
    if portfolio_quantities:
        real_quantities = {s: q for s, q in portfolio_quantities.items() if s in portfolio_holdings}
        weights, price_errors, _total_value = compute_real_weights(real_quantities)
        if weights:
            weights_are_real = True
        else:
            weights = {}
    else:
        weights = {}

    if not weights_are_real:
        n = len(portfolio_holdings) or 1
        weights = {symbol: 1.0 / n for symbol in portfolio_holdings}

    scenario = build_tier_shock_scenario(tiers)
    stress_result = run_stress_test(100_000.0, weights, scenario)
    scenario_pnl_pct = stress_result.portfolio_pnl / stress_result.portfolio_value_before

    volatilities: dict[str, float | None] = {}
    for symbol in portfolio_holdings:
        try:
            volatilities[symbol] = compute_annualized_volatility(symbol)
        except Exception:  # noqa: BLE001 -- volatility is supporting context, never fatal
            volatilities[symbol] = None

    correlation, drawdowns = _build_correlation_and_drawdown(portfolio_holdings)

    portfolio_impact = {
        "weights_are_real": weights_are_real,
        "weights": weights,
        "weights_disclosure": (
            "Computed from your real position quantities and live current prices."
            if weights_are_real
            else "ASSUMPTION: real position sizes were not provided for this request, so an equal weighting "
            "across the listed holdings was assumed. This is explicitly disclosed, not a silent default."
        ),
        "price_errors": price_errors,
        "exposure_tiers": tiers,
        "tier_shock_table": TIER_SHOCKS,
        "scenario_portfolio_pnl_pct": scenario_pnl_pct,
        "scenario_position_pnl": stress_result.position_pnl,
        "unshocked_holdings": stress_result.unshocked_assets,
        "assumptions_label": stress_result.assumptions_label,
        "annualized_volatility": volatilities,
        "correlation_matrix": correlation,
        "max_drawdown": drawdowns,
    }

    persona_assessments = compare_personas(
        weights=weights,
        weights_are_real=weights_are_real,
        industries=industries,
        tiers=tiers,
        scenario_pnl_pct=scenario_pnl_pct,
    )
    persona_comparison = [
        {
            "persona": a.persona,
            "display_name": a.display_name,
            "description": a.description,
            "constraint_violations": a.constraint_violations,
            "esg_notes": a.esg_notes,
            "verdict": a.verdict,
            "challenges_the_request": a.challenges_the_request,
        }
        for a in persona_assessments
    ]

    return portfolio_impact, persona_comparison, tiers, weights


def _summarize_message(message: dict) -> dict:
    role = message.get("role")
    blocks = []
    for block in message.get("content", []) or []:
        if not isinstance(block, dict):
            continue
        if "text" in block:
            blocks.append({"type": "text", "text": block["text"]})
        elif "toolUse" in block:
            tu = block["toolUse"]
            blocks.append({"type": "tool_use", "name": tu.get("name"), "input": tu.get("input")})
        elif "toolResult" in block:
            tr = block["toolResult"]
            content = tr.get("content") or []
            text_parts = [c.get("text") for c in content if isinstance(c, dict) and "text" in c]
            blocks.append({"type": "tool_result", "status": tr.get("status"), "content": text_parts or content})
        else:
            blocks.append({"type": "unknown", "raw": block})
    return {"role": role, "content": blocks}


@router.post("/investigate")
def investigate(request: InvestigateRequest):
    """Run the Ripple Investigation Agent (Bedrock/Strands) over an event description
    and a set of portfolio holdings. The agent establishes exposure itself, grounded in
    each holding's real (live-fetched) SEC filing and industry classification -- not a
    fixed semiconductor-only alias list -- so a utility holding a chip event is
    correctly reported as unexposed, and a tech holding an unrelated event isn't
    reflexively tied to chips either. Returns the agent's final answer plus a trace of
    every tool call it made (tool name, input, result) for UX/explainability.
    """
    # Cheap pre-check before the ~60s Bedrock agent run: does this event description
    # name anything specific enough to investigate (a proper noun, a material, a
    # sanctions-relevant term -- the same allowlist the exposure graph itself uses),
    # or is it a bare category word like "suppliers" with nothing to trace a ripple
    # from? Confirmed live: "suppliers" alone ran the full multi-tool agent loop for
    # ~60s only to conclude, in its own final answer, that it had nothing to go on.
    # Reusing extract_candidate_entities here (rather than a separate heuristic) means
    # this guard and the exposure graph agree on what counts as "specific" by
    # construction.
    candidates = extract_candidate_entities(request.event_description, max_candidates=5)

    # The candidate check alone misses a real case: a ticker is already given (so
    # "which company" is already resolved), and the event describes a real incident
    # type ("CEO fired", "plant explosion", "data breach") without naming a new
    # entity/material itself. That's specific enough to investigate -- confirmed live:
    # "ceo fired" + ticker "nvidia" was rejected by the candidate-only check even
    # though it's the exact kind of scoped governance question this tool should
    # answer. Allow it through when a ticker is given AND the event text has at least
    # two substantive (non-trivial, non-stopword) words -- still blocks a bare
    # one-word category ("suppliers", "news") even with a ticker given.
    _TRIVIAL_WORDS = {"a", "an", "the", "of", "for", "and", "or", "in", "on", "to", "news", "event"}
    substantive_words = [
        w for w in re.findall(r"[A-Za-z]+", request.event_description) if w.lower() not in _TRIVIAL_WORDS
    ]
    is_scoped_incident = bool(request.portfolio_holdings) and len(substantive_words) >= 2

    if not request.event_description.strip() or (not candidates and not is_scoped_incident):
        return {
            "event_description": request.event_description,
            "portfolio_holdings": request.portfolio_holdings,
            "answer": (
                "This event description doesn't name anything specific enough to investigate "
                "(a company, material, technology, sanctioned country, or named regulation). "
                "Try something like: \"New export controls restrict advanced semiconductor "
                "chips to China\" or \"EPA coal combustion residuals rule affecting coal-fired "
                "power plants.\""
            ),
            "trace": [],
            "error": None,
            "too_vague": True,
            "event_briefing": build_event_briefing(
                event_description=request.event_description,
                investigation_status="insufficient_evidence",
                tiers={},
                weights={},
                exposure_classifications={},
                followup_finding=None,
            ),
        }

    try:
        from app.riskripple.agents.definitions import build_ripple_investigator_agent
    except Exception as exc:
        raise HTTPException(500, f"Could not build agent (missing dependency?): {exc}") from exc

    try:
        agent = build_ripple_investigator_agent()
    except Exception as exc:
        raise HTTPException(500, f"Could not construct Bedrock agent: {exc}") from exc

    prompt = (
        f"Event: {request.event_description}\n"
        f"Portfolio holdings to investigate: {', '.join(request.portfolio_holdings)}\n\n"
        "Determine, with real evidence, whether and how each holding is exposed to this "
        "event, per your instructions. Do not assume any holding is or isn't relevant "
        "before checking."
    )

    try:
        result = agent(prompt)
    except Exception as exc:
        return {
            "event_description": request.event_description,
            "portfolio_holdings": request.portfolio_holdings,
            "answer": None,
            "trace": [],
            "error": f"{type(exc).__name__}: {exc}",
            "note": "Agent invocation failed -- likely missing/expired Bedrock credentials or model access in this region.",
            "event_briefing": build_event_briefing(
                event_description=request.event_description,
                investigation_status="failed",
                tiers={},
                weights={},
                exposure_classifications={},
                followup_finding=None,
            ),
        }

    raw_messages = [m if isinstance(m, dict) else dict(m) for m in agent.messages]
    trace = [_summarize_message(m) for m in raw_messages]

    exposure_classifications, followup_finding, industries = _extract_structured_findings(raw_messages)
    try:
        portfolio_impact, persona_comparison, tiers, weights = _build_portfolio_and_persona_sections(
            request.portfolio_holdings, request.portfolio_quantities, exposure_classifications, industries
        )
    except Exception as exc:  # noqa: BLE001 -- quant/persona sections are additive; never fail the whole response
        portfolio_impact = {"error": f"Could not compute portfolio impact: {type(exc).__name__}: {exc}"}
        persona_comparison = []
        tiers, weights = {}, {}

    event_briefing = build_event_briefing(
        event_description=request.event_description,
        investigation_status="completed",
        tiers=tiers,
        weights=weights,
        exposure_classifications=exposure_classifications,
        followup_finding=followup_finding,
    )
    for entry in persona_comparison:
        entry["attention_level"] = persona_attention_level(
            event_briefing["attention_level"], challenges_the_request=entry["challenges_the_request"]
        )

    response = {
        "event_description": request.event_description,
        "portfolio_holdings": request.portfolio_holdings,
        "answer": str(result),
        "trace": trace,
        "error": None,
        "exposure_classifications": exposure_classifications,
        "followup_investigation": followup_finding,
        "portfolio_impact": portfolio_impact,
        "persona_comparison": persona_comparison,
        "event_briefing": event_briefing,
    }
    if request.user_id:
        try:
            alerts_db.save_investigation_history(
                request.user_id, request.event_description, request.portfolio_holdings, response
            )
        except Exception:  # noqa: BLE001 -- history persistence is additive, never fail the response over it
            pass
    return response


@router.get("/investigate/history")
def investigate_history(user_id: str = Query(...), limit: int = Query(10, ge=1, le=50)):
    """Most recent completed manual investigations for `user_id` -- the Investigations
    page's third category, alongside confirmed_alerts and investigation_candidates."""
    return {"history": alerts_db.list_investigation_history(user_id, limit)}


@router.delete("/investigate/history/{entry_id}")
def delete_investigate_history(entry_id: int, user_id: str = Query(...)):
    """Deletes one past manual investigation. Scoped to `user_id` in the query itself
    (see `alerts_db.delete_investigation_history`) so a caller can only ever delete
    their own history, never another user's by guessing an id."""
    deleted = alerts_db.delete_investigation_history(user_id, entry_id)
    return {"deleted": deleted}


class AlertScanDocument(BaseModel):
    document_number: str
    title: str
    abstract: str | None = None
    publication_date: str | None = None
    document_url: str | None = None


class AlertScanRequest(BaseModel):
    documents: list[AlertScanDocument] | None = None
    search_term: str | None = None
    per_page: int = 10
    # When given, scans ONLY this caller-supplied portfolio instead of every real
    # user in the database -- what a "show my dashboard" request needs, as opposed
    # to the broad every-user sweep a background job would run. `user_id` keys the
    # dedup table (alerts.db.filter_unseen); pass the real authenticated user's id
    # so a scoped scan's dedup state doesn't collide with another real user's.
    portfolio_holdings: list[str] | None = None
    user_id: str | None = None


def _resolve_portfolios(portfolio_holdings: list[str] | None, user_id: str | None) -> dict[str, list[str]]:
    if portfolio_holdings:
        return {user_id or "caller": [t.strip().upper() for t in portfolio_holdings if t.strip()]}
    try:
        return get_all_portfolios()
    except Exception as exc:
        raise HTTPException(502, f"Could not read portfolios from the database: {exc}") from exc


_EMPTY_REGULATORY_SCAN_SHAPE = {
    "documents_scanned": 0, "portfolios_checked": 0, "alerts": [],
    "articles": [], "investigation_candidates": [], "confirmed_alerts": [],
}
_REGULATORY_SCAN_FRESHNESS_MINUTES = 10


def _perform_regulatory_scan(request: "AlertScanRequest", portfolios: dict[str, list[str]]) -> dict:
    if request.documents:
        documents = [d.model_dump() for d in request.documents]
    else:
        if request.search_term:
            result = regulatory_events.search_documents(term=request.search_term, per_page=request.per_page)
        else:
            # Broad, topic-agnostic pull (any agency, no keyword filter) rather
            # than the old 5-fixed-phrase semiconductor/export net -- see
            # search_documents_broad's docstring. The old narrow multi-term
            # search is still available via an explicit `search_term`. The
            # request's `per_page` default (10) is tuned for a single-term
            # search; a broad, unfiltered pull needs more volume to carry real
            # topic diversity, so use at least 40 here unless the caller asked
            # for more.
            result = regulatory_events.search_documents_broad(per_page=max(request.per_page, 40))
        documents = _dataclass_list(result.documents)

    for d in documents:
        d.setdefault("source", "regulatory")

    alerts = run_alert_scan(documents=documents, portfolios=portfolios)

    # Tier 1: every real regulatory document scanned, regardless of confirmation --
    # built directly from the fetched documents, same discipline as the news path's
    # `articles` (visibility must never depend on the relevance/verification gate).
    articles = [
        {
            "title": doc.get("title", ""),
            "url": doc.get("document_url"),
            "publication_date": doc.get("publication_date"),
            "agencies": doc.get("agencies"),
            "summary": _article_summary(doc),
        }
        for doc in documents
    ]

    investigation_candidates: list[dict] = []
    confirmed_alerts: list[dict] = []
    for alert in alerts:
        for match in alert.get("matches", []):
            entry = {
                "title": alert.get("title"),
                "document_url": alert.get("document_url"),
                "publication_date": alert.get("publication_date"),
                "source": "regulatory",
                **match,
            }
            (confirmed_alerts if match.get("is_confirmed_alert") else investigation_candidates).append(entry)

    return {
        "documents_scanned": len(documents),
        "portfolios_checked": len(portfolios),
        "alerts": alerts,
        "articles": articles,
        "investigation_candidates": investigation_candidates,
        "confirmed_alerts": confirmed_alerts,
    }


def _run_regulatory_scan_background(cache_key: str, request: "AlertScanRequest", portfolios: dict[str, list[str]]) -> None:
    try:
        result = _perform_regulatory_scan(request, portfolios)
    except Exception as exc:
        alerts_db.save_scan_error(cache_key, "regulatory", f"{type(exc).__name__}: {exc}")
        return
    alerts_db.save_scan_success(cache_key, "regulatory", result)


def _cached_regulatory_response(cache_key: str, status_if_missing: str = "idle") -> dict:
    cached = alerts_db.get_cached_scan(cache_key, "regulatory")
    base = (cached.get("result") if cached else None) or _EMPTY_REGULATORY_SCAN_SHAPE
    return {
        **base,
        "status": cached["status"] if cached else status_if_missing,
        "last_success_at": cached["last_success_at"] if cached else None,
        "error_message": (cached.get("error_message") if cached and cached["status"] == "error" else None),
    }


@router.post("/alerts/scan")
def alerts_scan(request: AlertScanRequest, background_tasks: BackgroundTasks):
    """Scan regulatory/sanctions documents against a real portfolio and return
    genuinely relevant alerts with a constrained recommendation for each. Pass
    `portfolio_holdings` (and ideally `user_id`) to scope the scan to one caller's
    real holdings; omit both to scan every real user's real portfolio from the
    app's own Postgres `portfolio_holdings` table instead (the background/ops use
    case). If `documents` isn't given, fetches live Federal Register documents (via
    `search_term`, or the existing broad default net) instead of requiring a caller
    to supply them.

    Same cache + background-refresh pattern as `/alerts/scan-news` (this path is
    faster in practice -- ~6-20s observed -- but the same immediate-response,
    background-refresh behavior keeps the frontend's handling consistent across both
    endpoints). `documents` supplied explicitly bypasses the cache entirely (used by
    tests/tools that want a synchronous result against a specific document set).
    """
    portfolios = _resolve_portfolios(request.portfolio_holdings, request.user_id)
    if not portfolios:
        return {**_EMPTY_REGULATORY_SCAN_SHAPE, "status": "idle", "last_success_at": None, "error_message": None}

    if request.documents:
        result = _perform_regulatory_scan(request, portfolios)
        return {**result, "status": "idle", "last_success_at": None, "error_message": None}

    cache_key = request.user_id or (
        ",".join(sorted(request.portfolio_holdings)) if request.portfolio_holdings else None
    )
    if not cache_key:
        result = _perform_regulatory_scan(request, portfolios)
        return {**result, "status": "idle", "last_success_at": None, "error_message": None}

    cached = alerts_db.get_cached_scan(cache_key, "regulatory")
    if not cached or (cached["status"] != "scanning" and not _scan_is_fresh(cached)):
        alerts_db.mark_scan_started(cache_key, "regulatory")
        background_tasks.add_task(_run_regulatory_scan_background, cache_key, request, portfolios)
        base = (cached.get("result") if cached else None) or _EMPTY_REGULATORY_SCAN_SHAPE
        return {
            **base, "status": "scanning",
            "last_success_at": cached["last_success_at"] if cached else None,
            "error_message": None,
        }

    return _cached_regulatory_response(cache_key)


@router.get("/alerts/scan/status")
def alerts_scan_status(user_id: str = Query(...)):
    """Read-only poll of the current cached regulatory-scan state for `user_id`."""
    return _cached_regulatory_response(user_id, status_if_missing="idle")


class AlertScanNewsRequest(BaseModel):
    # Raised from 5: confirmed live that 5 hid most of a ticker's real coverage
    # (e.g. the entire NVIDIA CEO-departure story). 10 is a deliberate middle ground,
    # not the max tested -- confirmed live that 20/ticker across 3 tickers pushed a
    # single synchronous scan past 150s once the direct-mention fix (below) started
    # correctly routing far more real articles through Stage-2 Bedrock verification.
    # This endpoint runs synchronously per request; real further coverage increases
    # need an async/background scan architecture, not just a higher number here --
    # noted as a follow-up, not solved in this pass.
    limit_per_ticker: int = 10
    # Same scoping as AlertScanRequest -- see _resolve_portfolios.
    portfolio_holdings: list[str] | None = None
    user_id: str | None = None


def _article_summary(doc: dict) -> str:
    text = (doc.get("abstract") or "").strip()
    if not text:
        return ""
    first_sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return first_sentence[:280]


_EMPTY_NEWS_SCAN_SHAPE = {
    "articles_scanned": 0, "portfolios_checked": 0, "alerts": [],
    "articles": [], "investigation_candidates": [], "confirmed_alerts": [],
    "diagnostics": {"per_ticker": {}, "error": None},
}

# How long a cached news-scan result is trusted before a refresh is kicked off in the
# background. A real scan is expensive (Bedrock verification per genuine candidate,
# confirmed live at 182s for a 3-ticker portfolio) -- this is not meant to be
# real-time, just fresh enough that a page load doesn't block on it.
_NEWS_SCAN_FRESHNESS_MINUTES = 10


def _perform_news_scan(portfolios: dict[str, list[str]], limit_per_ticker: int) -> dict:
    """The actual, expensive scan work -- real StocksFeed fetch + real Stage-2
    Bedrock verification across every genuine candidate. Pulled out of the route
    handler so it can be run either synchronously (no user_id to cache against -- the
    background/ops "scan everyone" case) or via FastAPI BackgroundTasks (the normal,
    per-user, page-load-triggered case) without duplicating logic.
    """
    all_tickers = sorted({ticker for symbols in portfolios.values() for ticker in symbols})
    documents, per_ticker_diag = news_stocksfeed.fetch_news_documents_for_tickers_diagnostic(
        all_tickers, limit_per_ticker=limit_per_ticker
    )

    failed_tickers = [t for t, d in per_ticker_diag.items() if d["error"]]
    all_failed = bool(all_tickers) and len(failed_tickers) == len(all_tickers)
    diagnostics = {
        "per_ticker": per_ticker_diag,
        "error": (
            f"StocksFeed failed for every requested ticker: {', '.join(failed_tickers)}. "
            "This is a degraded state, not confirmation of 'no news'."
        ) if all_failed else None,
    }

    # Tier 1: every real article, regardless of confirmation -- built directly from
    # the fetched documents, not from run_alert_scan's output, so visibility never
    # depends on the relevance/verification gate below.
    articles = [
        {
            "title": doc.get("title", ""),
            "url": doc.get("document_url"),
            "publication_date": doc.get("publication_date"),
            "ticker": doc.get("source_ticker"),
            "summary": _article_summary(doc),
        }
        for doc in documents
    ]

    alerts = run_alert_scan(documents=documents, portfolios=portfolios, strict_materials_only=True)

    investigation_candidates: list[dict] = []
    confirmed_alerts: list[dict] = []
    for alert in alerts:
        for match in alert.get("matches", []):
            entry = {
                "title": alert.get("title"),
                "document_url": alert.get("document_url"),
                "publication_date": alert.get("publication_date"),
                "source": "news",
                **match,
            }
            (confirmed_alerts if match.get("is_confirmed_alert") else investigation_candidates).append(entry)

    return {
        "articles_scanned": len(documents),
        "portfolios_checked": len(portfolios),
        "alerts": alerts,
        "articles": articles,
        "investigation_candidates": investigation_candidates,
        "confirmed_alerts": confirmed_alerts,
        "diagnostics": diagnostics,
    }


def _run_news_scan_background(cache_key: str, portfolios: dict[str, list[str]], limit_per_ticker: int) -> None:
    try:
        result = _perform_news_scan(portfolios, limit_per_ticker)
    except Exception as exc:
        alerts_db.save_scan_error(cache_key, "news", f"{type(exc).__name__}: {exc}")
        return
    alerts_db.save_scan_success(cache_key, "news", result)


def _scan_is_fresh(cached: dict | None) -> bool:
    if not cached or not cached.get("last_success_at"):
        return False
    # A cache row written by an older backend version (before the current response
    # shape/classification logic) must never be served as fresh, no matter how
    # recent -- confirmed live: this exact gap caused a real user to see zero
    # confirmed alerts the current code would actually find. Time-based freshness
    # only applies on top of a schema match.
    if cached.get("schema_version") != alerts_db.CURRENT_SCAN_SCHEMA_VERSION:
        return False
    from datetime import datetime, timedelta, timezone

    success_at = datetime.fromisoformat(cached["last_success_at"])
    return datetime.now(timezone.utc) - success_at < timedelta(minutes=_NEWS_SCAN_FRESHNESS_MINUTES)


def _cached_news_response(cache_key: str, status_if_missing: str = "idle") -> dict:
    cached = alerts_db.get_cached_scan(cache_key, "news")
    base = (cached.get("result") if cached else None) or _EMPTY_NEWS_SCAN_SHAPE
    return {
        **base,
        "status": cached["status"] if cached else status_if_missing,
        "last_success_at": cached["last_success_at"] if cached else None,
        "error_message": (cached.get("error_message") if cached and cached["status"] == "error" else None),
    }


@router.post("/alerts/scan-news")
def alerts_scan_news(request: AlertScanNewsRequest, background_tasks: BackgroundTasks):
    """Scan a real portfolio's actual held tickers' real recent news (via the app's
    existing StocksFeed integration). Returns THREE distinct tiers, per the product
    requirement that news visibility never depend on the confirmed-alert threshold:

    - `articles`: every real, deduplicated article found for a held ticker --
      headline, publisher URL, date, ticker, a short factual one-line summary --
      regardless of whether it became a candidate or an alert. Never empty just
      because nothing was confirmed; only empty if there's genuinely no real news.
    - `investigation_candidates`: articles with a real entity/relationship match
      (direct mention or a supply-chain/material link) that did NOT clear Stage-2
      verification as alert-worthy -- plausible, not confirmed.
    - `confirmed_alerts`: the strict, evidence-gated tier. For a direct news mention
      specifically, "materially significant" is NOT enough on its own -- promotion
      requires the article itself to report a concrete, quantified transmission
      signal (see `verification._classify_direct_news`'s 5-level distinction);
      a real, significant story with no quantified signal lands in
      `investigation_candidates` instead. Each confirmed entry carries a
      `source: "news"` marker (never upgraded to the filing path's `verified_fact`
      confidence language merely for being news-sourced) plus `classification_tier`
      and `exposure_mechanism` for the frontend to render the distinction.

    This scan is expensive (real Stage-2 Bedrock verification per genuine candidate --
    confirmed live at 182s for a 3-ticker portfolio) and MUST NOT block a page load.
    When `user_id` (or, failing that, the sorted portfolio_holdings) is given as a
    cache key: this returns IMMEDIATELY with the last cached result (status 'idle' if
    fresh, 'scanning' if a refresh was just kicked off in the background, 'error' with
    the last good result still attached if the last refresh failed) rather than
    blocking on a fresh scan. Poll `GET /alerts/scan-news/status` to see when a
    background refresh completes. Only the background/ops "scan every real user"
    case (no portfolio_holdings or user_id given) still runs synchronously, since
    there's no single per-caller cache key for it.
    """
    portfolios = _resolve_portfolios(request.portfolio_holdings, request.user_id)
    if not portfolios:
        return {**_EMPTY_NEWS_SCAN_SHAPE, "status": "idle", "last_success_at": None, "error_message": None}

    cache_key = request.user_id or (
        ",".join(sorted(request.portfolio_holdings)) if request.portfolio_holdings else None
    )
    if not cache_key:
        result = _perform_news_scan(portfolios, request.limit_per_ticker)
        return {**result, "status": "idle", "last_success_at": None, "error_message": None}

    cached = alerts_db.get_cached_scan(cache_key, "news")
    if not cached or (cached["status"] != "scanning" and not _scan_is_fresh(cached)):
        alerts_db.mark_scan_started(cache_key, "news")
        background_tasks.add_task(_run_news_scan_background, cache_key, portfolios, request.limit_per_ticker)
        base = (cached.get("result") if cached else None) or _EMPTY_NEWS_SCAN_SHAPE
        return {
            **base, "status": "scanning",
            "last_success_at": cached["last_success_at"] if cached else None,
            "error_message": None,
        }

    return _cached_news_response(cache_key)


@router.get("/alerts/scan-news/status")
def alerts_scan_news_status(user_id: str = Query(...)):
    """Read-only poll of the current cached news-scan state for `user_id` -- never
    triggers a new scan itself (that only happens from the POST endpoint above)."""
    return _cached_news_response(user_id, status_if_missing="idle")

"""Trickle-down investigation routes: sanctions/regulatory/macro data ingestion reads,
plus the Ripple Investigation Agent (Bedrock/Strands) tying them together with the
company exposure graph and RAG retrieval over filings.

Ported from riskripple-ai (see app/riskripple/). Only the research/regulatory/exposure
tool surface was brought over -- finance and persona tooling are a separate pass.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.riskripple.alerts.db import get_all_portfolios
from app.riskripple.alerts.pipeline import run_alert_scan
from app.riskripple.ingestion import macro_fred, news_stocksfeed, regulatory_events, sanctions_gac, sanctions_ofac
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
    if not request.event_description.strip() or not candidates:
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
        }

    trace = [_summarize_message(m) for m in agent.messages]
    return {
        "event_description": request.event_description,
        "portfolio_holdings": request.portfolio_holdings,
        "answer": str(result),
        "trace": trace,
        "error": None,
    }


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


@router.post("/alerts/scan")
def alerts_scan(request: AlertScanRequest):
    """Scan regulatory/sanctions documents against a real portfolio and return
    genuinely relevant alerts with a constrained recommendation for each. Pass
    `portfolio_holdings` (and ideally `user_id`) to scope the scan to one caller's
    real holdings; omit both to scan every real user's real portfolio from the
    app's own Postgres `portfolio_holdings` table instead (the background/ops use
    case). If `documents` isn't given, fetches live Federal Register documents (via
    `search_term`, or the existing broad default net) instead of requiring a caller
    to supply them.
    """
    if request.documents:
        documents = [d.model_dump() for d in request.documents]
    else:
        try:
            if request.search_term:
                result = regulatory_events.search_documents(term=request.search_term, per_page=request.per_page)
            else:
                result = regulatory_events.search_documents_multi(per_page=request.per_page)
        except Exception as exc:
            raise HTTPException(502, f"Federal Register fetch failed: {exc}") from exc
        documents = _dataclass_list(result.documents)

    portfolios = _resolve_portfolios(request.portfolio_holdings, request.user_id)
    if not portfolios:
        return {"documents_scanned": len(documents), "portfolios_checked": 0, "alerts": []}

    alerts = run_alert_scan(documents=documents, portfolios=portfolios)
    return {"documents_scanned": len(documents), "portfolios_checked": len(portfolios), "alerts": alerts}


class AlertScanNewsRequest(BaseModel):
    limit_per_ticker: int = 5
    # Same scoping as AlertScanRequest -- see _resolve_portfolios.
    portfolio_holdings: list[str] | None = None
    user_id: str | None = None


@router.post("/alerts/scan-news")
def alerts_scan_news(request: AlertScanNewsRequest):
    """Scan a real portfolio's actual held tickers' real recent news (via the app's
    existing StocksFeed integration), checking each article against EVERY holding
    in the portfolio (not just the ticker the article was fetched for) -- a news
    item about one holding can be a real trickle-down risk to another via the same
    evidence-gated exposure graph `/alerts/scan` already uses for regulatory
    documents. Reuses that exact same relevance/recommendation pipeline; only the
    document source differs. Pass `portfolio_holdings` (and ideally `user_id`) to
    scope to one caller's real holdings; omit both to scan every real user's real
    portfolio instead.

    Most real news (earnings notes, analyst calls, executive gossip) is not a
    trickle-down risk event, so articles are pre-filtered to ones containing an
    independent trade/export/sanctions/supply-chain signal before being checked --
    see `ingestion.news_stocksfeed._has_trade_signal`.
    """
    portfolios = _resolve_portfolios(request.portfolio_holdings, request.user_id)
    if not portfolios:
        return {"articles_scanned": 0, "portfolios_checked": 0, "alerts": []}

    all_tickers = sorted({ticker for symbols in portfolios.values() for ticker in symbols})
    try:
        documents = news_stocksfeed.fetch_news_documents_for_tickers(
            all_tickers, limit_per_ticker=request.limit_per_ticker
        )
    except Exception as exc:
        raise HTTPException(502, f"StocksFeed fetch failed: {exc}") from exc

    alerts = run_alert_scan(documents=documents, portfolios=portfolios, strict_materials_only=True)
    return {"articles_scanned": len(documents), "portfolios_checked": len(portfolios), "alerts": alerts}

"""Strands Agent assembly for the trickle-down investigation agents (ported from
riskripple-ai; the quant-analyst and persona-reporting agents were intentionally left
out of this port since their tools weren't brought over).

UNTESTED LIVE: invoking these agents requires bedrock:InvokeModel, which is
access-denied on the personal AWS account used for development (see
docs/KNOWN_LIMITATIONS.md). The tool functions each agent wires in are fully tested
independently (see backend/tests/tools/); what is NOT yet verified is the LLM's tool
selection and conversational orchestration on top of them. Before the hackathon demo,
run scripts/verify_bedrock_agent.py against the temporary AWS account to confirm
BEDROCK_MODEL_ID is enabled in the account's region, then smoke-test each agent once.
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from app.riskripple.tools.exposure_tools import ALL_EXPOSURE_TOOLS
from app.riskripple.tools.regulatory_tools import ALL_REGULATORY_TOOLS
from app.riskripple.tools.research_tools import ALL_RESEARCH_TOOLS

# Not assumed to be enabled in any given account/region -- verify with
# `aws bedrock list-foundation-models` on the hackathon account before the demo, per
# the master spec's instruction not to assume access to a specific model.
#
# Must be an inference-profile ID, not the bare model ID, for this model/account --
# confirmed live on the hackathon account (637423589728, us-east-1):
# on-demand invocation of the bare "anthropic.claude-sonnet-4-5-20250929-v1:0" fails
# with ValidationException ("on-demand throughput isn't supported ... retry with an
# inference profile"). `aws bedrock list-inference-profiles --region us-east-1`
# confirmed "us.anthropic.claude-sonnet-4-5-20250929-v1:0" is the correct ID.
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")


def _bedrock_model() -> BedrockModel:
    return BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=BEDROCK_REGION)


REGULATORY_WATCHDOG_PROMPT = """You are the Regulatory Watchdog agent for RiskRipple AI.
Your job is to detect new or changed regulatory/geopolitical events relevant to the
investment universe. Use list_new_documents to find candidate publications, then use
create-event-style structured output (title, jurisdiction, affected entities/sectors,
source references, confidence) for each one. Never fabricate a document or a
jurisdiction that isn't in the tool output. If evidence is thin, set confidence low
and say so explicitly rather than overstating certainty."""

REGULATORY_INVESTIGATOR_PROMPT = """You are the Regulatory Intelligence Investigator
agent for RiskRipple AI. Given a regulatory event, use search_sanctions_records,
retrieve_company_filings, resolve_entity_aliases, and summarize_event_evidence to
build a cited, evidence-grounded summary. Distinguish legal/regulatory restrictions
(sanctions, export controls) from broader economic/market exposure. Never state that
an entity is legally sanctioned unless search_sanctions_records returned a match for
it -- a thematic or industry similarity is not a sanctions match. State uncertainty
explicitly when evidence is thin or absent."""

EXPOSURE_MAPPER_PROMPT = """You are the Exposure and Contagion Mapper agent for
RiskRipple AI. Use resolve_company_identity, load_company_graph,
find_direct_exposure_tool, traverse_relationships_tool, and calculate_exposure_weights
to connect a regulatory event to portfolio holdings via verified relationships only.
Never state a relationship exists unless it came from load_company_graph's output,
which only includes relationships with literal textual evidence. Report "no
established link" rather than guessing when a holding isn't connected to the event
within the traversal depth searched."""

RIPPLE_INVESTIGATOR_PROMPT = """You are the Ripple Investigation agent for RiskRipple
AI. You are given an event description and a set of portfolio holdings. Nothing about
which holdings are exposed has been decided yet -- you must establish that yourself,
with real evidence, for THESE specific holdings and THIS specific event. Never assume
a holding is exposed because another holding is, because it shares a sector label with
one that is, or because an event "sounds like" it should matter to a certain industry.
A semiconductor export-control event is not automatically relevant to every portfolio
you see; a copper or ESG event is not automatically irrelevant to a tech company either.

Start by calling load_company_graph(portfolio_symbols, event_description=<the event
text>). This fetches each holding's REAL, current SEC filing (live, for any ticker --
not a fixed demo list) and returns: (1) its real industry classification
(`industries`, e.g. "Electric Services" vs. "Semiconductors & Related Devices"), and
(2) any literal textual evidence connecting it to known chip-supply-chain entities AND
to candidate entities/materials extracted from the event text itself. Then use
find_direct_exposure_tool / traverse_relationships_tool / calculate_exposure_weights to
classify each holding as direct, indirect, or no_established_link. "no_established_link"
is a correct, honest answer when a holding's real business has no real connection to
the event -- say so plainly, citing its real industry classification, rather than
inventing a connection or staying silent about holdings that don't fit the narrative.

For holdings that DO show initial evidence, look BEYOND the fixed alias lists for
additional ripple effects: new entities, materials, technologies, or relationships
this specific event names that load_company_graph's fixed KNOWN_SUPPLIER_ALIASES
doesn't already catch. Use propose_candidate_entities to surface more candidates from
the event text, then use search_filings_fulltext and search_sec_edgar_live to check
whether any held company's real filing disclosure actually supports a connection.
hybrid_search_evidence is the preferred first call for an open-ended question about
one holding ("does this company's filing say anything about X?") -- it combines
literal textual matching with real semantic retrieval over the Knowledge Base in one
call, and always prefer its literal_matches over its semantic_evidence when both are
present, since a literal match is the stronger claim.
Never treat a candidate as a relationship until a tool call has found literal textual
evidence for it.

Classify every claim you make into exactly one of: verified_fact (directly supported
by a tool's returned evidence or a deterministic calculation), evidence_supported_
hypothesis (a plausible mechanism with partial real evidence), unverified_possibility
(worth investigating further, but no supporting evidence found), or simulated_outcome
(explicitly assumption-based, never your own generated number). A verified competitor
relationship does not by itself prove that competitor's price will move -- say so.
Stop once you've checked the candidates you found or hit your round/tool-call budget;
do not keep inventing new questions indefinitely. If you find nothing beyond the
already-confirmed matches, say that plainly rather than manufacturing a hypothesis to
seem thorough."""


def build_ripple_investigator_agent() -> Agent:
    return Agent(
        model=_bedrock_model(),
        tools=ALL_RESEARCH_TOOLS + ALL_REGULATORY_TOOLS + ALL_EXPOSURE_TOOLS,
        system_prompt=RIPPLE_INVESTIGATOR_PROMPT,
    )


def build_regulatory_watchdog_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_REGULATORY_TOOLS[:1], system_prompt=REGULATORY_WATCHDOG_PROMPT)


def build_regulatory_investigator_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_REGULATORY_TOOLS, system_prompt=REGULATORY_INVESTIGATOR_PROMPT)


def build_exposure_mapper_agent() -> Agent:
    return Agent(model=_bedrock_model(), tools=ALL_EXPOSURE_TOOLS, system_prompt=EXPOSURE_MAPPER_PROMPT)

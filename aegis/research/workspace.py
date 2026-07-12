"""Research workspace builder for V2.0-C."""

from __future__ import annotations

from typing import Any

from aegis.models.common import Market
from aegis.models.research import ResearchEvidenceLink, ResearchNote, ResearchWorkspace


def build_research_workspace(
    *,
    symbol: str,
    market: Market,
    notes: list[ResearchNote],
    evidence: list[ResearchEvidenceLink],
    created_at: str,
) -> dict[str, Any]:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    missing_evidence: list[str] = []
    unverified_claims: list[str] = []
    unresolved_questions: list[str] = []

    for note in notes:
        unresolved_questions.extend(note.open_questions)
        for evidence_id in note.evidence_ids:
            linked = evidence_by_id.get(evidence_id)
            if linked is None:
                missing_evidence.append(evidence_id)
                continue
            if linked.status != "verified":
                unverified_claims.append(evidence_id)

    verified_evidence_count = sum(1 for item in evidence if item.status == "verified")
    decision_summary = (
        f"{symbol} research workspace has {len(notes)} notes and "
        f"{verified_evidence_count} verified evidence links."
    )
    workspace = ResearchWorkspace(
        workspace_id=f"research_{market}_{symbol}_v2_0_c",
        symbol=symbol,
        market=market,
        notes=notes,
        evidence=evidence,
        decision_summary=decision_summary,
        unresolved_questions=sorted(set(unresolved_questions)),
        created_at=created_at,
        updated_at=created_at,
    )
    return {
        "workspace": workspace.model_dump(),
        "quality": {
            "note_count": len(notes),
            "evidence_count": len(evidence),
            "verified_evidence_count": verified_evidence_count,
            "missing_evidence": sorted(set(missing_evidence)),
            "unverified_claims": sorted(set(unverified_claims)),
            "accepted_for_decision_support": not missing_evidence and not unverified_claims,
        },
        "safety": {
            "read_only": True,
            "no_real_trade": True,
            "no_broker_api": True,
            "no_webhook": True,
            "no_strategy_mutation": True,
            "dashboard_contract_unchanged": True,
            "llm_unverified_not_evidence": True,
        },
    }


def render_research_workspace_markdown(report: dict[str, Any]) -> str:
    workspace = report["workspace"]
    quality = report["quality"]
    lines = [
        "# V2.0-C Research Workspace",
        "",
        f"- workspace_id: `{workspace['workspace_id']}`",
        f"- symbol: `{workspace['symbol']}`",
        f"- market: `{workspace['market']}`",
        f"- accepted_for_decision_support: `{quality['accepted_for_decision_support']}`",
        f"- verified_evidence_count: `{quality['verified_evidence_count']}`",
        "",
        "## Notes",
        "",
    ]
    for note in workspace["notes"]:
        lines.extend(
            [
                f"### {note['title']}",
                "",
                f"- thesis: {note['thesis']}",
                f"- decision_relevance: {note['decision_relevance']}",
                f"- evidence_ids: `{', '.join(note['evidence_ids'])}`",
                "",
            ]
        )
    lines.extend(["## Evidence", ""])
    for item in workspace["evidence"]:
        lines.append(
            "- "
            f"{item['evidence_id']} "
            f"type=`{item['evidence_type']}` "
            f"status=`{item['status']}` "
            f"title={item['title']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Research notes are read-only decision support.",
            "- Unverified LLM output is not accepted evidence.",
            "- No real trade, broker API, webhook, strategy mutation, or Dashboard Contract change.",
            "",
        ]
    )
    return "\n".join(lines)

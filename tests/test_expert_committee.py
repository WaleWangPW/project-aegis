"""Phase 3 tests for ExpertCommittee — PHASE3 doc §9.5."""

from __future__ import annotations

from aegis.experts.base import BaseExpertAgent
from aegis.experts.committee import DEFAULT_AGENT_CLASSES, ExpertCommittee
from aegis.experts.context import AnalysisContext
from aegis.models.candidate import Candidate
from aegis.models.common import DataQuality
from aegis.models.expert_opinion import ExpertOpinion


def _candidate(symbol="AAA") -> Candidate:
    return Candidate(
        candidate_id=f"cand_20260703_US_{symbol}",
        symbol=symbol,
        market="US",
        source="universe_builder",
        filter_reason=["liquidity_ok"],
        liquidity_ok=True,
        data_quality=DataQuality(status="complete"),
        created_at="2026-07-03T07:31:00-07:00",
    )


def _context(symbol="AAA") -> AnalysisContext:
    return AnalysisContext(date="2026-07-03", session="pre_market", candidate=_candidate(symbol), signals=[])


class _BrokenAgent(BaseExpertAgent):
    name = "BrokenAgent"

    def analyze(self, context):
        raise RuntimeError("simulated agent failure")


def test_committee_runs_all_7_agents_in_deterministic_order():
    committee = ExpertCommittee()
    assert len(committee.agents) == 7
    assert [type(a) for a in committee.agents] == DEFAULT_AGENT_CLASSES


def test_one_candidate_produces_7_opinions():
    committee = ExpertCommittee()
    opinions = committee.analyze_candidate(_context())
    assert len(opinions) == 7
    assert all(isinstance(o, ExpertOpinion) for o in opinions)


def test_two_candidates_produce_14_opinions():
    committee = ExpertCommittee()
    contexts = [_context("AAA"), _context("BBB")]
    opinions = committee.analyze_candidates(contexts)
    assert len(opinions) == 14


def test_agent_failure_is_converted_to_neutral_opinion_not_a_crash():
    committee = ExpertCommittee(agents=[_BrokenAgent()])
    opinions = committee.analyze_candidate(_context())

    assert len(opinions) == 1
    opinion = opinions[0]
    assert isinstance(opinion, ExpertOpinion)
    assert opinion.stance == "neutral"
    assert "agent_execution_failed" in opinion.missing_data
    assert "simulated agent failure" in opinion.summary

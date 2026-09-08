import pytest

from ai_paper_search.query import is_relevant, plan_queries, plan_query


def test_llm_mas_query_uses_two_concepts_and_nlp_extension():
    plan = plan_query("llm multi agent system")
    assert len(plan.concept_groups) == 2
    assert plan.use_nlp_extension
    assert is_relevant(
        "AgentVerse: Facilitating Multi-Agent Collaboration",
        "A framework using large language model agents.",
        plan,
    )
    assert not is_relevant("Multi-Agent Path Finding", None, plan)


def test_query_variants_are_deduplicated_and_bounded():
    plans = plan_queries(
        "llm multi agent system",
        [
            "Societies of language model agents",
            " societies  of language-model agents ",
            "Collective decision making with generative agents",
        ],
    )
    assert [plan.original for plan in plans] == [
        "llm multi agent system",
        "Societies of language model agents",
        "Collective decision making with generative agents",
    ]

    with pytest.raises(ValueError, match="at most 5"):
        plan_queries("agents", [f"variant {index}" for index in range(6)])

from __future__ import annotations

import inspect

import pytest

import fossil_core.adapters.mcp as canonical_mcp
import fossil_core.agent as legacy_agent
from fossil_core.ports.capability import CapabilityError


EXPECTED_TOOLS = (
    "fossil.search",
    "fossil.read",
    "fossil.lineage",
    "fossil.propose",
    "fossil.validate",
    "fossil.commit",
    "fossil.manage",
)


def test_thin_mcp_adapter_legacy_identity_and_allowlist_are_frozen():
    assert canonical_mcp.__all__ == ["ThinMCPAdapter"]
    assert legacy_agent.ThinMCPAdapter is canonical_mcp.ThinMCPAdapter
    assert legacy_agent.CapabilityError is CapabilityError
    assert canonical_mcp.ThinMCPAdapter.__module__ == "fossil_core.adapters.mcp"
    assert canonical_mcp.ThinMCPAdapter.TOOL_NAMES == EXPECTED_TOOLS

    adapter = canonical_mcp.ThinMCPAdapter(
        service=object(), access=object(), context=object()
    )
    assert adapter.list_tools() == list(EXPECTED_TOOLS)


def test_thin_mcp_adapter_call_shapes_are_unchanged():
    init_parameters = list(
        inspect.signature(canonical_mcp.ThinMCPAdapter.__init__).parameters.values()
    )
    assert [parameter.name for parameter in init_parameters] == [
        "self",
        "service",
        "access",
        "context",
    ]
    assert init_parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in init_parameters[1:]
    )
    assert all(
        parameter.default is inspect.Parameter.empty for parameter in init_parameters
    )

    invoke_parameters = list(
        inspect.signature(canonical_mcp.ThinMCPAdapter.invoke).parameters.values()
    )
    assert [parameter.name for parameter in invoke_parameters] == [
        "self",
        "tool_name",
        "arguments",
    ]
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for parameter in invoke_parameters
    )
    assert all(
        parameter.default is inspect.Parameter.empty for parameter in invoke_parameters
    )


def test_thin_mcp_adapter_rejects_graph_escape_with_same_error_type():
    adapter = canonical_mcp.ThinMCPAdapter(
        service=object(), access=object(), context=object()
    )

    with pytest.raises(
        CapabilityError, match="not in the FOSSIL agent capability surface"
    ):
        adapter.invoke("neo4j.cypher", {"query": "MATCH (n) DETACH DELETE n"})

    with pytest.raises(
        CapabilityError, match="not in the FOSSIL agent capability surface"
    ):
        adapter.invoke("graphiti.add_episode", {"content": "bypass durable event"})

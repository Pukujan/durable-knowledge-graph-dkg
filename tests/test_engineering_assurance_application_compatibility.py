from __future__ import annotations

import inspect
from pathlib import Path

import fossil_core.application.engineering.assurance as canonical_assurance
import fossil_core.engineering_assurance as legacy_assurance


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_IMPLICIT_NAMESPACE = {
    "Any",
    "CONTROL_PLANE_VERSION",
    "Mapping",
    "Path",
    "REQUIRED_CORRELATION_FIELDS",
    "annotations",
    "json",
    "load_control_plane_contract",
    "semantic_http_errors",
    "validate_control_plane_contract",
}

SEMANTIC_SYMBOLS = (
    "CONTROL_PLANE_VERSION",
    "REQUIRED_CORRELATION_FIELDS",
    "semantic_http_errors",
    "validate_control_plane_contract",
    "load_control_plane_contract",
)


def test_engineering_assurance_legacy_namespace_and_identity_are_frozen():
    assert not hasattr(legacy_assurance, "__all__")
    assert {
        name for name in vars(legacy_assurance) if not name.startswith("_")
    } == EXPECTED_IMPLICIT_NAMESPACE

    for name in SEMANTIC_SYMBOLS:
        assert getattr(legacy_assurance, name) is getattr(canonical_assurance, name)


def test_engineering_assurance_call_shapes_are_unchanged():
    semantic = list(
        inspect.signature(canonical_assurance.semantic_http_errors).parameters.values()
    )
    assert [parameter.name for parameter in semantic] == ["status_code", "body", "expected"]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in semantic)
    assert semantic[2].default == "json"

    validate = list(
        inspect.signature(canonical_assurance.validate_control_plane_contract).parameters.values()
    )
    assert [parameter.name for parameter in validate] == ["contract"]
    assert validate[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD

    load = list(
        inspect.signature(canonical_assurance.load_control_plane_contract).parameters.values()
    )
    assert [parameter.name for parameter in load] == ["root"]
    assert load[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_engineering_assurance_representative_behavior_matches_legacy_path():
    samples = (
        {"status_code": 200, "body": b""},
        {"status_code": 200, "body": b"{"},
        {"status_code": 200, "body": b'{"ok":true}'},
        {"status_code": 503, "body": b"unavailable"},
    )
    for sample in samples:
        assert legacy_assurance.semantic_http_errors(**sample) == canonical_assurance.semantic_http_errors(**sample)

    canonical_contract = canonical_assurance.load_control_plane_contract(ROOT)
    legacy_contract = legacy_assurance.load_control_plane_contract(ROOT)
    assert legacy_contract == canonical_contract
    assert legacy_assurance.validate_control_plane_contract(legacy_contract) == canonical_assurance.validate_control_plane_contract(canonical_contract) == []

from __future__ import annotations

import importlib

from kai_mind.core.services.legacy_slot_layer_map import SLOT_LAYER_BY_ID

CONSUMER_MODULES = (
    "kai_mind.core.services.system_map_v1_to_v2_adapter",
    "kai_mind.core.services.system_map_v2_normalize_service",
)


def _bound_mapping(module_name: str) -> object:
    # Runtime reflection on purpose: the consumers only import the name,
    # so mypy strict (no implicit re-export) rightly refuses a direct
    # `from <consumer> import SLOT_LAYER_BY_ID` here.
    return vars(importlib.import_module(module_name))["SLOT_LAYER_BY_ID"]


def test_slot_layer_map_has_one_shared_source() -> None:
    """The v1 adapter and the v2 normalize service must bind the very
    same mapping object, so v1/v2 layer equivalence no longer depends on
    two copies happening to stay identical.
    """
    for module_name in CONSUMER_MODULES:
        assert _bound_mapping(module_name) is SLOT_LAYER_BY_ID


def test_slot_layer_map_covers_the_legacy_thirteen_slots() -> None:
    assert len(SLOT_LAYER_BY_ID) == 13

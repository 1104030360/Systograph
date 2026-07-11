from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CapabilityReferenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CapabilityReferencePlane(CapabilityReferenceModel):
    id: str
    label: str
    description: str
    display_order: int = Field(ge=1)
    visual_group: str | None = None


class CapabilityReferenceNode(CapabilityReferenceModel):
    id: str
    plane_id: str
    label: str
    description: str
    display_order: int = Field(ge=1)
    aliases: tuple[str, ...] = ()
    icon_hint: str | None = None
    token_hint: str | None = None
    activation_applicable: bool


class CapabilityReferenceCatalog(CapabilityReferenceModel):
    catalog_id: str
    version: str
    display_name: str
    description: str
    planes: tuple[CapabilityReferencePlane, ...]
    nodes: tuple[CapabilityReferenceNode, ...]

    @model_validator(mode="after")
    def validate_structure(self) -> CapabilityReferenceCatalog:
        plane_ids = [plane.id for plane in self.planes]
        if len(plane_ids) != len(set(plane_ids)):
            raise ValueError("duplicate plane id")
        plane_orders = [plane.display_order for plane in self.planes]
        if len(plane_orders) != len(set(plane_orders)):
            raise ValueError("duplicate plane display_order")
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("duplicate node id")
        known_plane_ids = set(plane_ids)
        if any(node.plane_id not in known_plane_ids for node in self.nodes):
            raise ValueError("node references unknown plane_id")
        node_orders = [
            (node.plane_id, node.display_order) for node in self.nodes
        ]
        if len(node_orders) != len(set(node_orders)):
            raise ValueError("duplicate node display_order")
        return self

    @property
    def plane_ids(self) -> tuple[str, ...]:
        return tuple(plane.id for plane in self.planes)

    def node(self, node_id: str) -> CapabilityReferenceNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(node_id)

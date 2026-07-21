from __future__ import annotations

from kai_mind.core.models.profile_registry_projection import (
    ProfileRegistryProjection,
    ProfileRegistryProjectionEntry,
)
from kai_mind.core.services.profile_registry_loader import (
    ProfileMetadataRegistry,
)
from kai_mind.core.services.profile_rule_definitions import (
    MVP_CAPABILITY_PROFILE_IDS,
)


class ProfileRegistryProjectionService:
    @staticmethod
    def project(
        registry: ProfileMetadataRegistry,
    ) -> ProfileRegistryProjection:
        validated = registry.require_profile_ids(MVP_CAPABILITY_PROFILE_IDS)
        profiles = tuple(
            ProfileRegistryProjectionEntry(
                profile_id=item.profile_id,
                display_name=item.display_name,
                short_label=item.short_label,
                description=item.description,
                primary_axis=item.primary_axis,
                secondary_axes=item.secondary_axes,
                display_order=item.display_order,
                default_uncertainty=item.default_uncertainty,
                recommended_next_checks=item.recommended_next_checks,
            )
            for item in sorted(
                validated.profiles,
                key=lambda profile: profile.display_order,
            )
        )
        return ProfileRegistryProjection(profiles=profiles)

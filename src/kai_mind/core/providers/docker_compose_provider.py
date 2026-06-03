"""Parse Docker Compose files into low-level scan facts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.models.scan import ParseIssue, ProviderScanResult, ScanFact
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.services.rule_catalog_loader import RuleCatalogLoader
from kai_mind.core.services.secret_masking_service import SecretMaskingService

DOCKER_COMPOSE_PARSE_STAGE: Literal["docker_compose_parse"] = (
    "docker_compose_parse"
)
DOCKER_COMPOSE_PROVIDER_NAME = "docker_compose"
DOCKER_COMPOSE_PARSE_ERROR_RULE_ID = "docker_compose_parse_error"
DOCKER_COMPOSE_PARSE_ERROR_KIND = "parse_error"
DOCKER_SERVICE_KIND = "docker_service"
PUBLISHED_PORT_KIND = "published_port"
DOCKER_ENVIRONMENT_KIND = "docker_environment"
DOCKER_ENV_FILE_KIND = "docker_env_file"
DOCKER_VOLUME_KIND = "docker_volume"
DOCKER_DEPENDS_ON_KIND = "docker_depends_on"
GENERIC_IMAGE_RULE_ID = "docker_service_image_detected"
PUBLISHED_PORT_RULE_ID = "docker_published_port_detected"
ENVIRONMENT_RULE_ID = "docker_environment_detected"
ENV_FILE_RULE_ID = "docker_env_file_detected"
VOLUME_RULE_ID = "docker_volume_detected"
DEPENDS_ON_RULE_ID = "docker_depends_on_detected"
COMPOSE_FILENAMES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}
PORT_FIELD_ORDER = (
    "host_ip",
    "published",
    "target",
    "protocol",
    "app_protocol",
    "mode",
    "name",
)
VOLUME_FIELD_ORDER = ("source", "target", "type", "read_only")


class DockerComposeProvider:
    """Read supported Compose files from deterministic inventory input."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        image_rule_catalog_path: Path | str | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        image_rules = RuleCatalogLoader().load_docker_image_rules(
            image_rule_catalog_path,
        )
        self._image_rule_ids = {
            rule.repository: rule.rule_id for rule in image_rules
        }

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root)

        for record in inventory.files:
            if not self._is_compose_path(record.path):
                continue

            file_result = self._collect_file(
                project_root / record.path,
                relative_path=record.path,
            )
            result.facts.extend(file_result.facts)
            result.evidence.extend(file_result.evidence)
            result.issues.extend(file_result.issues)

        return result

    def _collect_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        try:
            loaded = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            self._append_parse_error(
                result,
                file=relative_path,
                message=self._format_parse_error_message(exc),
            )
            return result

        if loaded is None:
            return result
        if not isinstance(loaded, Mapping):
            self._append_parse_error(
                result,
                file=relative_path,
                message=(
                    "Failed to parse Docker Compose file: root is not a map"
                ),
            )
            return result

        services = loaded.get("services")
        if not isinstance(services, Mapping):
            self._append_parse_error(
                result,
                file=relative_path,
                message=(
                    "Failed to parse Docker Compose file: "
                    "services is not a map"
                ),
            )
            return result

        for service_name, service_data in services.items():
            service_key = str(service_name)
            if not isinstance(service_data, Mapping):
                self._append_parse_error(
                    result,
                    file=relative_path,
                    message=(
                        "Failed to parse Docker Compose service "
                        f"{service_key}: service definition is not a map"
                    ),
                    path=f"services.{service_key}",
                )
                continue
            self._collect_service(
                result,
                file=relative_path,
                service_name=service_key,
                service_data=service_data,
            )

        return result

    def _collect_service(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        service_name: str,
        service_data: Mapping[Any, Any],
    ) -> None:
        image = service_data.get("image")
        if image is not None:
            self._append_fact(
                result,
                file=file,
                path=f"services.{service_name}.image",
                value=str(image),
                kind=DOCKER_SERVICE_KIND,
                rule_id=self._image_rule_id(str(image)),
            )

        self._collect_ports(result, file, service_name, service_data)
        self._collect_environment(result, file, service_name, service_data)
        self._collect_env_file(result, file, service_name, service_data)
        self._collect_volumes(result, file, service_name, service_data)
        self._collect_depends_on(result, file, service_name, service_data)

    def _collect_ports(
        self,
        result: ProviderScanResult,
        file: str,
        service_name: str,
        service_data: Mapping[Any, Any],
    ) -> None:
        ports = service_data.get("ports")
        if not isinstance(ports, Sequence) or isinstance(ports, str):
            return

        for index, port in enumerate(ports):
            value = self._render_ordered_mapping(port, PORT_FIELD_ORDER)
            if value is None:
                value = str(port)
            self._append_fact(
                result,
                file=file,
                path=f"services.{service_name}.ports[{index}]",
                value=value,
                kind=PUBLISHED_PORT_KIND,
                rule_id=PUBLISHED_PORT_RULE_ID,
            )

    def _collect_environment(
        self,
        result: ProviderScanResult,
        file: str,
        service_name: str,
        service_data: Mapping[Any, Any],
    ) -> None:
        environment = service_data.get("environment")
        if isinstance(environment, Mapping):
            for key, value in environment.items():
                key_name = str(key)
                self._append_environment_fact(
                    result,
                    file=file,
                    path=f"services.{service_name}.environment.{key_name}",
                    key_name=key_name,
                    value=None if value is None else str(value),
                )
            return

        if not isinstance(environment, Sequence) or isinstance(
            environment,
            str,
        ):
            return

        for entry in environment:
            key_name, value = self._split_environment_entry(str(entry))
            self._append_environment_fact(
                result,
                file=file,
                path=f"services.{service_name}.environment.{key_name}",
                key_name=key_name,
                value=value,
            )

    def _collect_env_file(
        self,
        result: ProviderScanResult,
        file: str,
        service_name: str,
        service_data: Mapping[Any, Any],
    ) -> None:
        env_file = service_data.get("env_file")
        entries = self._as_list(env_file)
        for index, entry in enumerate(entries):
            value = self._env_file_value(entry)
            if value is None:
                continue
            self._append_fact(
                result,
                file=file,
                path=f"services.{service_name}.env_file[{index}]",
                value=value,
                kind=DOCKER_ENV_FILE_KIND,
                rule_id=ENV_FILE_RULE_ID,
            )

    def _collect_volumes(
        self,
        result: ProviderScanResult,
        file: str,
        service_name: str,
        service_data: Mapping[Any, Any],
    ) -> None:
        volumes = service_data.get("volumes")
        if not isinstance(volumes, Sequence) or isinstance(volumes, str):
            return

        for index, volume in enumerate(volumes):
            value = self._render_ordered_mapping(volume, VOLUME_FIELD_ORDER)
            if value is None:
                value = str(volume)
            self._append_fact(
                result,
                file=file,
                path=f"services.{service_name}.volumes[{index}]",
                value=value,
                kind=DOCKER_VOLUME_KIND,
                rule_id=VOLUME_RULE_ID,
            )

    def _collect_depends_on(
        self,
        result: ProviderScanResult,
        file: str,
        service_name: str,
        service_data: Mapping[Any, Any],
    ) -> None:
        depends_on = service_data.get("depends_on")
        if isinstance(depends_on, Mapping):
            names = [str(name) for name in depends_on]
        elif isinstance(depends_on, Sequence) and not isinstance(
            depends_on,
            str,
        ):
            names = [str(name) for name in depends_on]
        else:
            return

        for index, dependency_name in enumerate(names):
            self._append_fact(
                result,
                file=file,
                path=f"services.{service_name}.depends_on[{index}]",
                value=dependency_name,
                kind=DOCKER_DEPENDS_ON_KIND,
                rule_id=DEPENDS_ON_RULE_ID,
            )

    def _append_environment_fact(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        key_name: str,
        value: str | None,
    ) -> None:
        masked_value = None
        if value is not None:
            masked_value = self._masking_service.mask_value(
                value,
                key=key_name,
            )
            masked_value = self._masking_service.mask_text(masked_value)

        self._append_fact(
            result,
            file=file,
            path=path,
            value=masked_value,
            kind=DOCKER_ENVIRONMENT_KIND,
            rule_id=ENVIRONMENT_RULE_ID,
        )

    def _append_parse_error(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        message: str,
        path: str = "$parse_error",
    ) -> None:
        masked_message = self._masking_service.mask_text(message)
        result.issues.append(
            ParseIssue(
                provider=DOCKER_COMPOSE_PROVIDER_NAME,
                scan_stage=DOCKER_COMPOSE_PARSE_STAGE,
                file=file,
                message=masked_message,
                rule_id=DOCKER_COMPOSE_PARSE_ERROR_RULE_ID,
            )
        )
        result.evidence.append(
            Evidence(
                id=self._evidence_id(
                    file,
                    path,
                    DOCKER_COMPOSE_PARSE_ERROR_RULE_ID,
                ),
                kind=DOCKER_COMPOSE_PARSE_ERROR_KIND,
                file=file,
                path=path,
                value=masked_message,
                rule_id=DOCKER_COMPOSE_PARSE_ERROR_RULE_ID,
            )
        )

    def _append_fact(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        value: str | None,
        kind: str,
        rule_id: str,
    ) -> None:
        result.facts.append(
            ScanFact(
                kind=kind,
                file=file,
                path=path,
                value=value,
                rule_id=rule_id,
            )
        )
        result.evidence.append(
            Evidence(
                id=self._evidence_id(file, path, rule_id),
                kind=kind,
                file=file,
                path=path,
                value=value,
                rule_id=rule_id,
            )
        )

    def _evidence_id(self, file: str, path: str, rule_id: str) -> str:
        digest_source = f"{file}:{path}:{rule_id}".encode()
        digest = hashlib.sha1(digest_source).hexdigest()
        return f"evidence:{rule_id}:{file}:{digest[:12]}"

    def _format_parse_error_message(self, exc: Exception) -> str:
        problem = getattr(exc, "problem", None)
        message = problem or getattr(exc, "msg", None) or str(exc)
        return f"Failed to parse Docker Compose file: {message}"

    def _image_rule_id(self, image: str) -> str:
        normalized = image.lower().split("@", maxsplit=1)[0]
        repository = normalized.split(":", maxsplit=1)[0]
        return self._image_rule_ids.get(repository, GENERIC_IMAGE_RULE_ID)

    def _render_ordered_mapping(
        self,
        value: Any,
        field_order: Sequence[str],
    ) -> str | None:
        if not isinstance(value, Mapping):
            return None

        parts = [
            f"{field}={value[field]}"
            for field in field_order
            if field in value and value[field] is not None
        ]
        return ",".join(parts)

    def _split_environment_entry(self, entry: str) -> tuple[str, str | None]:
        if "=" not in entry:
            return entry, None
        key, value = entry.split("=", maxsplit=1)
        return key, value

    def _env_file_value(self, entry: Any) -> str | None:
        if isinstance(entry, Mapping):
            path = entry.get("path")
            if path is None:
                return None
            return str(path)
        return str(entry)

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _is_compose_path(self, relative_path: str) -> bool:
        return Path(relative_path).name in COMPOSE_FILENAMES

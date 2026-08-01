"""SSRF egress policy for explicit query trace requests."""

from __future__ import annotations

import socket
from dataclasses import dataclass
from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
)
from typing import Literal, Protocol
from urllib.parse import SplitResult, urlsplit, urlunsplit

IPAddress = IPv4Address | IPv6Address
EgressPolicyMode = Literal["safe", "local-dev"]
EgressBlockReason = Literal[
    "invalid_url",
    "unsupported_scheme",
    "missing_hostname",
    "userinfo_not_allowed",
    "invalid_port",
    "dns_resolution_failed",
    "host_not_allowed",
    "port_not_allowed",
    "metadata_blocked",
    "loopback_blocked",
    "private_network_blocked",
    "link_local_blocked",
    "unspecified_blocked",
    "multicast_blocked",
    "reserved_blocked",
    "non_global_blocked",
]


@dataclass(frozen=True)
class EgressPolicyConfig:
    mode: EgressPolicyMode = "safe"
    allow_loopback: bool = False
    allowed_hosts: tuple[str, ...] = ()
    allowed_ports: tuple[int, ...] = ()


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: EgressBlockReason | None = None
    normalized_url: str | None = None
    normalized_host: str | None = None
    port: int | None = None
    resolved_ips: tuple[str, ...] = ()


class HostResolver(Protocol):
    def resolve(self, hostname: str, port: int) -> tuple[IPAddress, ...]: ...


class SocketHostResolver:
    """Resolve all stream-capable IPv4/IPv6 addresses for one host."""

    def resolve(self, hostname: str, port: int) -> tuple[IPAddress, ...]:
        addresses: list[IPAddress] = []
        seen: set[IPAddress] = set()
        address_info = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
        for family, _type, _protocol, _canonical, sockaddr in address_info:
            if family not in {socket.AF_INET, socket.AF_INET6}:
                continue
            address = ip_address(str(sockaddr[0]).split("%", maxsplit=1)[0])
            if address not in seen:
                seen.add(address)
                addresses.append(address)
        return tuple(addresses)


_METADATA_ADDRESSES = frozenset(
    {
        ip_address("169.254.169.254"),
        ip_address("fd00:ec2::254"),
    }
)
_PRIVATE_NETWORKS: tuple[IPv4Network | IPv6Network, ...] = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
    IPv6Network("fc00::/7"),
)


class EgressPolicy:
    def __init__(
        self,
        *,
        config: EgressPolicyConfig | None = None,
        resolver: HostResolver | None = None,
    ) -> None:
        self._config = config or EgressPolicyConfig()
        self._resolver = resolver or SocketHostResolver()
        self._allowed_hosts = frozenset(
            host.strip().lower()
            for host in self._config.allowed_hosts
            if host.strip()
        )
        self._allowed_ports = frozenset(self._config.allowed_ports)

    def evaluate(self, url: str) -> EgressDecision:
        parsed, blocked = self._parse(url)
        if blocked is not None:
            return blocked
        assert parsed is not None

        hostname = parsed.hostname
        assert hostname is not None
        normalized_host = hostname.lower()
        try:
            port = parsed.port or self._default_port(parsed.scheme)
        except ValueError:
            return EgressDecision(allowed=False, reason="invalid_port")

        if self._config.mode == "local-dev":
            if normalized_host not in self._allowed_hosts:
                return EgressDecision(
                    allowed=False,
                    reason="host_not_allowed",
                    normalized_host=normalized_host,
                    port=port,
                )
            if port not in self._allowed_ports:
                return EgressDecision(
                    allowed=False,
                    reason="port_not_allowed",
                    normalized_host=normalized_host,
                    port=port,
                )

        normalized_url = self._normalized_url(
            parsed,
            hostname=normalized_host,
            port=port,
        )
        # Track A SSRF baseline: validate all DNS answers immediately before
        # request dispatch. The transport may resolve again, so this is not
        # equivalent to pinned-IP DNS rebinding protection.
        addresses = self._addresses(normalized_host, port)
        if addresses is None or not addresses:
            return EgressDecision(
                allowed=False,
                reason="dns_resolution_failed",
                normalized_url=normalized_url,
                normalized_host=normalized_host,
                port=port,
            )

        resolved_ips = tuple(str(address) for address in addresses)
        for address in addresses:
            reason = self._blocked_reason(address)
            if reason is None:
                continue
            if (
                reason == "loopback_blocked"
                and self._config.mode == "local-dev"
                and self._config.allow_loopback
            ):
                continue
            return EgressDecision(
                allowed=False,
                reason=reason,
                normalized_url=normalized_url,
                normalized_host=normalized_host,
                port=port,
                resolved_ips=resolved_ips,
            )

        return EgressDecision(
            allowed=True,
            normalized_url=normalized_url,
            normalized_host=normalized_host,
            port=port,
            resolved_ips=resolved_ips,
        )

    def _parse(
        self,
        url: str,
    ) -> tuple[SplitResult | None, EgressDecision | None]:
        try:
            parsed = urlsplit(url)
            scheme = parsed.scheme.lower()
            hostname = parsed.hostname
        except ValueError:
            return None, EgressDecision(allowed=False, reason="invalid_url")

        if scheme not in {"http", "https"}:
            return None, EgressDecision(
                allowed=False,
                reason="unsupported_scheme",
            )
        if hostname is None:
            return None, EgressDecision(
                allowed=False,
                reason="missing_hostname",
            )
        if "@" in parsed.netloc:
            return None, EgressDecision(
                allowed=False,
                reason="userinfo_not_allowed",
            )
        try:
            _ = parsed.port
        except ValueError:
            return None, EgressDecision(
                allowed=False,
                reason="invalid_port",
            )
        return parsed._replace(scheme=scheme), None

    def _addresses(
        self,
        hostname: str,
        port: int,
    ) -> tuple[IPAddress, ...] | None:
        literal = hostname.split("%", maxsplit=1)[0]
        try:
            return (ip_address(literal),)
        except ValueError:
            pass

        try:
            return self._resolver.resolve(hostname, port)
        except (OSError, socket.gaierror, ValueError):
            return None

    def _blocked_reason(
        self,
        address: IPAddress,
    ) -> EgressBlockReason | None:
        classified_address: IPAddress = address
        if (
            isinstance(address, IPv6Address)
            and address.ipv4_mapped is not None
        ):
            classified_address = address.ipv4_mapped

        if classified_address in _METADATA_ADDRESSES:
            return "metadata_blocked"
        if classified_address.is_unspecified:
            return "unspecified_blocked"
        if classified_address.is_loopback:
            return "loopback_blocked"
        if classified_address.is_link_local:
            return "link_local_blocked"
        if any(classified_address in network for network in _PRIVATE_NETWORKS):
            return "private_network_blocked"
        if classified_address.is_multicast:
            return "multicast_blocked"
        if classified_address.is_reserved:
            return "reserved_blocked"
        if not classified_address.is_global:
            return "non_global_blocked"
        return None

    def _default_port(self, scheme: str) -> int:
        return 443 if scheme == "https" else 80

    def _normalized_url(
        self,
        parsed: SplitResult,
        *,
        hostname: str,
        port: int,
    ) -> str:
        default_port = self._default_port(parsed.scheme)
        display_host = f"[{hostname}]" if ":" in hostname else hostname
        netloc = (
            display_host if port == default_port else f"{display_host}:{port}"
        )
        return urlunsplit(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                "",
                "",
            )
        )

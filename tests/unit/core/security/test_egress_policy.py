from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address

import pytest

from kai_mind.core.security.egress_policy import (
    EgressPolicy,
    EgressPolicyConfig,
    IPAddress,
)


@dataclass(frozen=True)
class FakeResolver:
    answers: dict[str, tuple[str, ...]]

    def resolve(
        self,
        hostname: str,
        port: int,
    ) -> tuple[IPAddress, ...]:
        del port
        if hostname not in self.answers:
            raise OSError("DNS resolution failed")
        return tuple(ip_address(value) for value in self.answers[hostname])


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("example.com/api", "unsupported_scheme"),
        ("file:///etc/passwd", "unsupported_scheme"),
        ("gopher://127.0.0.1:6379", "unsupported_scheme"),
        ("ftp://example.com/file", "unsupported_scheme"),
        ("http:///path", "missing_hostname"),
        ("http://user:pass@example.com", "userinfo_not_allowed"),
        ("https://expected-host:fake@evil-host", "userinfo_not_allowed"),
        ("http://example.com:99999/", "invalid_port"),
        ("http://[::1", "invalid_url"),
    ],
)
def test_given_invalid_or_unsafe_url_shape_when_evaluated_then_it_is_blocked(
    url: str,
    reason: str,
) -> None:
    policy = EgressPolicy(
        resolver=FakeResolver({"example.com": ("93.184.216.34",)})
    )

    decision = policy.evaluate(url)

    assert decision.allowed is False
    assert decision.reason == reason
    assert decision.resolved_ips == ()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/api",
        "http://10.0.0.5:8080/api",
        "http://172.16.0.5:8080/api",
        "http://172.31.255.255:8080/api",
        "http://192.168.1.5:8080/api",
        "http://169.254.1.1/api",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0:8000/api",
        "http://100.64.0.1/",
        "http://192.0.2.1/",
        "http://198.51.100.1/",
        "http://203.0.113.1/",
        "http://198.18.0.1/",
        "http://224.0.0.1/",
        "http://240.0.0.1/",
        "http://[::1]:8000/api",
        "http://[fc00::1]/api",
        "http://[fe80::1]/api",
        "http://[::]:8000/api",
        "http://[::ffff:127.0.0.1]:8000/api",
    ],
)
def test_given_non_global_ip_literal_when_evaluated_then_safe_mode_blocks_it(
    url: str,
) -> None:
    decision = EgressPolicy(resolver=FakeResolver({})).evaluate(url)

    assert decision.allowed is False
    assert decision.reason is not None


@pytest.mark.parametrize(
    ("hostname", "answer", "reason"),
    [
        ("localhost", "127.0.0.1", "loopback_blocked"),
        ("evil.example.test", "127.0.0.1", "loopback_blocked"),
        ("2130706433", "127.0.0.1", "loopback_blocked"),
        ("0x7f000001", "127.0.0.1", "loopback_blocked"),
        ("017700000001", "127.0.0.1", "loopback_blocked"),
        (
            "rebind.example.test",
            "192.168.1.10",
            "private_network_blocked",
        ),
        (
            "metadata.example.test",
            "169.254.169.254",
            "metadata_blocked",
        ),
        ("link-local.example.test", "169.254.1.1", "link_local_blocked"),
    ],
)
def test_hostname_resolving_to_unsafe_ip_is_blocked(
    hostname: str,
    answer: str,
    reason: str,
) -> None:
    policy = EgressPolicy(resolver=FakeResolver({hostname: (answer,)}))

    decision = policy.evaluate(f"http://{hostname}:8000/api")

    assert decision.allowed is False
    assert decision.reason == reason
    assert decision.resolved_ips == (answer,)


def test_any_unsafe_dns_answer_blocks_whole_host() -> None:
    policy = EgressPolicy(
        resolver=FakeResolver(
            {
                "mixed.example.test": (
                    "93.184.216.34",
                    "192.168.1.10",
                )
            }
        )
    )

    decision = policy.evaluate("https://mixed.example.test/api")

    assert decision.allowed is False
    assert decision.reason == "private_network_blocked"
    assert decision.resolved_ips == ("93.184.216.34", "192.168.1.10")


def test_given_dns_failure_when_evaluated_then_request_is_blocked() -> None:
    decision = EgressPolicy(resolver=FakeResolver({})).evaluate(
        "https://missing.example.test/api"
    )

    assert decision.allowed is False
    assert decision.reason == "dns_resolution_failed"


def test_given_public_dns_answers_when_evaluated_then_request_is_allowed() -> (
    None
):
    policy = EgressPolicy(
        resolver=FakeResolver(
            {"example.com": ("93.184.216.34", "2606:2800:220:1::")}
        )
    )

    decision = policy.evaluate("HTTPS://Example.COM/api#fragment")

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.normalized_host == "example.com"
    assert decision.normalized_url == "https://example.com/api"
    assert decision.port == 443
    assert decision.resolved_ips == (
        "93.184.216.34",
        "2606:2800:220:1::",
    )


def test_local_dev_allows_explicit_loopback_host_and_port() -> None:
    policy = EgressPolicy(
        config=EgressPolicyConfig(
            mode="local-dev",
            allow_loopback=True,
            allowed_hosts=("localhost",),
            allowed_ports=(11434,),
        ),
        resolver=FakeResolver({"localhost": ("127.0.0.1", "::1")}),
    )

    decision = policy.evaluate("http://LOCALHOST:11434/api/generate")

    assert decision.allowed is True
    assert decision.normalized_host == "localhost"
    assert decision.port == 11434


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("http://localhost:8000/api", "port_not_allowed"),
        ("http://127.0.0.1:11434/api", "host_not_allowed"),
        ("http://192.168.1.10:11434/api", "host_not_allowed"),
    ],
)
def test_given_local_dev_target_outside_exact_allowlist_then_it_is_blocked(
    url: str,
    reason: str,
) -> None:
    policy = EgressPolicy(
        config=EgressPolicyConfig(
            mode="local-dev",
            allow_loopback=True,
            allowed_hosts=("localhost",),
            allowed_ports=(11434,),
        ),
        resolver=FakeResolver({"localhost": ("127.0.0.1",)}),
    )

    decision = policy.evaluate(url)

    assert decision.allowed is False
    assert decision.reason == reason


def test_given_local_dev_metadata_target_then_it_remains_blocked() -> None:
    policy = EgressPolicy(
        config=EgressPolicyConfig(
            mode="local-dev",
            allow_loopback=True,
            allowed_hosts=("metadata.example.test",),
            allowed_ports=(80,),
        ),
        resolver=FakeResolver({"metadata.example.test": ("169.254.169.254",)}),
    )

    decision = policy.evaluate("http://metadata.example.test/latest/meta-data")

    assert decision.allowed is False
    assert decision.reason == "metadata_blocked"


def test_blocked_userinfo_decision_does_not_echo_credentials() -> None:
    secret = "synthetic-secret-139"

    decision = EgressPolicy(resolver=FakeResolver({})).evaluate(
        f"http://user:{secret}@example.com/api?token={secret}"
    )

    serialized = repr(decision)
    assert decision.reason == "userinfo_not_allowed"
    assert secret not in serialized

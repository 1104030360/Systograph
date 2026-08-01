# GitHub #139 Query Trace SSRF Egress Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Date reviewed:** 2026-06-23

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/139

**Goal:** 防止 query trace 對 metadata、loopback、private/link-local network、unspecified address 或未授權 endpoint 發送請求。

**Verdict on proposed plan:** 方向正確，可以解 #139 的 MVP security baseline；但必須補上下列落地約束，否則仍可能留下 SSRF bypass：

- egress policy 必須接在 shared `EndpointCallProvider` boundary，涵蓋 web `/api/trace` 與 CLI `systograph trace`。
- local-dev 放行設定不可只讀被掃描 repo 的 `pyproject.toml`，否則惡意 repo 可自行開啟 localhost/private egress；必須是 Systograph operator-controlled opt-in。
- DNS resolve 後檢查能擋「hostname 解析到 private/metadata」這類 case，但不能宣稱已完成 production-grade DNS pinning；若要完全處理 DNS rebinding TOCTOU，還需要 pinned-IP transport 或 network-layer egress deny。
- 若 #139 reviewer 要求「DNS rebinding 完整關閉」而不是「baseline 風險降低」，本 PR 必須採用 pinned connect target 或 network-layer deny；單次 preflight DNS check 不可被描述成完整修復。
- blocked case 的 provider result 必須 `query_sent=false`，且不能呼叫 HTTP client；service/API 層也要保證不產生 `request_sent` event。

---

## 0. Verified Sources And Current Evidence

### GitHub Issue

- Issue #139 is open as of 2026-06-23.
- Title: `[Security][High][H-1] fix: enforce SSRF egress policy for query trace`
- Issue goals:
  - Parse hostname/DNS before applying IP egress policy.
  - Handle DNS rebinding risk.
  - Deny metadata, private, link-local, unspecified, and loopback by default.
  - Blocked case must keep `query_sent=false` and not call provider.

### Current Repo Observations

- `src/systograph/core/providers/endpoint_call_provider.py`
  - `EndpointCallProvider.__init__()` currently creates `httpx.Client()` with default settings.
  - `_endpoint_preflight_result()` only checks scheme is `http` or `https`.
  - `_request()` directly calls `self._client.request(...)`.
  - No hostname, DNS, IP range, metadata, proxy, or redirect policy is enforced.

- `src/systograph/core/services/query_trace_service.py`
  - `QueryTraceService.trace()` finds the endpoint by `endpoint_id`, then calls `EndpointCallProvider.call(...)`.
  - It creates a `request_sent` event before calling the provider, but drops that event when `call_result.query_sent` is false.
  - This is compatible with blocked SSRF behavior, but needs a regression test for `blocked_endpoint`.

- `src/systograph/web/routes/trace_routes.py`
  - `/api/trace` loads the project map and `retrieved_chunks_keys`, then calls `QueryTraceService.trace(...)`.
  - Current project trace config is loaded from the scanned project root.

- `src/systograph/cli/trace_command.py`
  - `systograph trace` also constructs `QueryTraceService()` directly.
  - The fix must cover CLI and web through shared core code, not just the route.

- Existing tests:
  - `tests/unit/core/test_endpoint_call_provider.py` covers happy path, timeout, invalid URL, and unsupported scheme.
  - `tests/unit/core/test_query_trace_service.py` already verifies unsupported endpoints emit only an error event and `query_sent=false`.
  - `tests/web/test_trace_routes.py` verifies route masking and config behavior.

### External Security References

- OWASP SSRF Prevention Cheat Sheet:
  - SSRF is not limited to HTTP schemes.
  - URL/domain/IP validation and allowlist-oriented controls are recommended.
  - Redirect following should be disabled to prevent validation bypass.
  - DNS pinning/rebinding risk must be considered.
  - URL: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

- PortSwigger Web Security Academy SSRF:
  - SSRF lets server-side code request unintended locations.
  - Loopback and internal/private services are common SSRF targets.
  - URL parser tricks, userinfo, alternative IP representations, and redirect bypasses matter.
  - URL: https://portswigger.net/web-security/ssrf

- HTTPX docs:
  - HTTPX does not follow redirects by default, but `follow_redirects=False` should still be explicit for this path.
  - HTTPX reads proxy-related environment variables by default unless `trust_env=False`.
  - URLs:
    - https://www.python-httpx.org/compatibility/#redirects
    - https://www.python-httpx.org/environment_variables/

- Python `ipaddress` docs:
  - Standard address properties include `is_private`, `is_loopback`, `is_link_local`, `is_unspecified`, `is_multicast`, `is_reserved`, and `is_global`.
  - URL: https://docs.python.org/3/library/ipaddress.html

- IANA special-purpose registries:
  - IPv4 and IPv6 special-purpose ranges are not generally safe egress targets.
  - URLs:
    - https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml
    - https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml

- AWS EC2 IMDS:
  - AWS instance metadata examples use `http://169.254.169.254/...`.
  - URL: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html

---

## 1. Security Problem Definition

Query trace is an explicit runtime feature, but its endpoint comes from the scanned map. The scanned repo/config/system map must be treated as untrusted input for network egress.

Current risk path:

1. A scanned project influences `ai_system_map.endpoints[].value`.
2. Web `/api/trace` or CLI `systograph trace` selects an endpoint by `endpoint_id`.
3. `EndpointCallProvider` sends one HTTP request to `endpoint.value`.
4. If `endpoint.value` points to metadata, loopback, private, link-local, unspecified, or a hostname resolving to those ranges, Systograph can become an SSRF proxy or network reachability oracle.

Risk examples:

- `http://169.254.169.254/latest/meta-data/`
- `http://127.0.0.1:6379/`
- `http://localhost:11434/api/generate`
- `http://10.0.0.5:8080/`
- `http://172.16.0.5:8080/` through `http://172.31.255.255:8080/`
- `http://192.168.1.5:8080/`
- `http://169.254.1.1/`
- `http://[::1]:8000/`
- `http://[fe80::1]/`
- `http://0.0.0.0:8000/`
- `http://[::]:8000/`
- `http://safe-looking.example.test/` resolving to any unsafe IP.

---

## 2. Security Invariants

The implementation is complete only if all invariants hold:

1. Every query trace HTTP request goes through a single egress policy before `httpx` sees the request.
2. The policy checks the parsed URL, normalized host, port, DNS results, and every resolved IPv4/IPv6 address.
3. Safe mode denies loopback, private, link-local, metadata, unspecified, multicast, reserved, and any non-global destination by default.
4. DNS failure is a block, not a fallback-to-request.
5. Any unsafe resolved IP blocks the whole endpoint, even if other resolved IPs look safe.
6. Redirect following is disabled at request time.
7. Environment proxy routing is disabled for the default production client with `trust_env=False`.
8. Blocked result returns:
   - provider `status="blocked_endpoint"`
   - `query_sent=false`
   - `error_type="egress_policy_blocked"`
   - sanitized `error_message`
9. Blocked result never calls the HTTP client or transport.
10. `QueryTraceService` must not emit `request_sent` for blocked endpoints.
11. Existing missing-endpoint behavior remains unchanged: `endpoint_not_found`, `query_sent=false`, and no provider call.
12. Static map build, scan, viewer load, and replay paths must still not instantiate `EndpointCallProvider` or send runtime traffic.

---

## 3. Scope

### In Scope

- Query trace SSRF egress policy for `EndpointCallProvider`.
- URL parse, scheme allowlist, hostname/userinfo/port validation.
- DNS resolver abstraction for deterministic tests.
- IP address classification using Python standard library plus explicit metadata ranges.
- Default safe mode.
- Explicit local-dev opt-in from trusted operator-controlled configuration.
- Web and CLI behavior alignment.
- Regression tests for blocked destinations, DNS resolution, provider no-call behavior, and legitimate allowed public endpoint behavior.
- API/security docs update.

### Out Of Scope

- Enterprise firewall, Kubernetes NetworkPolicy, cloud VPC egress controls.
- Full proxy policy engine.
- Dynamic remote allowlist service.
- Automatic rewrite of scanned project config.
- Complete production-grade DNS pinning in the MVP.
- Full cloud metadata threat model.
- Turning query trace into a general observability platform.

Important limitation:

- Resolve-before-request reduces DNS rebinding risk and catches hostnames already resolving to unsafe IPs.
- It does not fully remove DNS time-of-check/time-of-use risk if the HTTP stack resolves the hostname again later.
- Do not claim full DNS pinning unless this PR also pins the connection to the validated IP or adds network-layer egress restrictions.

Decision gate before implementation:

- **Track A: MVP baseline.** Resolve immediately before request, block unsafe answers, disable redirects/proxies, and document residual DNS TOCTOU. This is acceptable only if #139 is interpreted as a baseline SSRF egress policy.
- **Track B: full DNS rebinding closure.** Ensure the policy check and actual connect target use the same validated address set, or enforce a network-layer deny for unsafe ranges. Choose this track if the reviewer treats DNS rebinding as a hard close condition.
- The PR description must state which track was implemented.

---

## 4. Design Decision

### 4.1 New Module Boundary

Prefer a security-owned module instead of a generic service module:

- Create: `src/systograph/core/security/__init__.py`
- Create: `src/systograph/core/security/egress_policy.py`

Reason:

- This is not business service logic.
- The same policy can later be reused by remote template import or other opt-in network features.
- It keeps the security invariant separate from query trace orchestration.

### 4.2 Provider-Level Enforcement

`EndpointCallProvider` is the mandatory enforcement point.

`QueryTraceService`, web routes, and CLI may pass configuration, but they must not be the only guard. If a future caller uses `EndpointCallProvider` directly, it should still be protected by default.

### 4.3 Trace Result Status

Recommended MVP contract:

- Add provider status: `EndpointCallStatus` includes `"blocked_endpoint"`.
- Keep top-level `TraceRunResult.status="partial"` for blocked endpoint, because current public trace status union is `"completed" | "partial" | "endpoint_not_found" | "error"`.
- Use `TraceRunResult.query_sent=false`.
- Use `TraceRunResult.error_reason="egress_policy_blocked"`.
- Error event:
  - `event_type="error"`
  - `query_sent=false`
  - `status="blocked"`
  - `error.type="egress_policy_blocked"`

If the UI/product requires top-level `status="blocked_endpoint"`, then this issue must also update:

- `src/systograph/core/models/trace.py`
- `docs/API-GUIDE.md`
- `schemas/ai-system-map.v1.schema.json` if schema generation is affected
- route and frontend expectations

Do not silently introduce a schema-breaking top-level status.

---

## 5. Data Model

Implement with dataclasses and literal types unless the surrounding code needs Pydantic validation.

```python
from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address
from typing import Literal, Protocol

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
    allow_private_network: bool = False
    allow_link_local: bool = False
    allowed_hosts: tuple[str, ...] = ()
    allowed_ports: tuple[int, ...] = ()
    allowed_cidrs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: EgressBlockReason | None = None
    normalized_url: str | None = None
    normalized_host: str | None = None
    port: int | None = None
    resolved_ips: tuple[str, ...] = ()


class HostResolver(Protocol):
    def resolve(self, hostname: str, port: int) -> tuple[IPAddress, ...]:
        ...
```

Notes:

- `resolved_ips` must be safe to log: IPs are acceptable; do not include URL userinfo, query string, body, or raw endpoint config.
- `normalized_url` should omit credentials and fragments.
- If `allowed_cidrs` is not implemented in this issue, keep the field out until a future intranet mode exists.

---

## 6. Policy Rules

### 6.1 URL Parse

- Use `urllib.parse.urlsplit()`.
- Reject parse errors with `invalid_url`.
- Allow only `http` and `https`.
- Reject missing scheme as `unsupported_scheme`.
- Reject non-HTTP schemes:
  - `file`
  - `ftp`
  - `gopher`
  - `data`
  - `dict`
  - `postgresql`
  - any other scheme

### 6.2 Hostname, Userinfo, And Port

- `parsed.hostname` must exist.
- Reject userinfo:
  - `http://user:pass@example.com`
  - `https://expected-host:fake@evil-host`
- Normalize host for comparison:
  - lowercase
  - no credentials
  - preserve enough original host info for DNS resolution
- Normalize port:
  - explicit port must be valid.
  - default `http` to `80`.
  - default `https` to `443`.

### 6.3 IP Literal Handling

Before DNS:

- Try `ipaddress.ip_address(hostname)`.
- IPv4 and bracketed IPv6 literals should be classified directly.
- IPv4-mapped IPv6 should also classify the mapped IPv4 address, for example `::ffff:127.0.0.1`.
- Link-local IPv6 with a zone id must still be treated as link-local.

### 6.4 DNS Resolution

- Use a resolver abstraction, not direct `socket.getaddrinfo()` in tests.
- Default resolver may use:
  - `socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)`
- Collect all IPv4/IPv6 addresses.
- DNS failure blocks with `dns_resolution_failed`.
- Empty result blocks with `dns_resolution_failed`.
- If any resolved IP is unsafe, block the whole endpoint.
- Never fall back to sending the original hostname when resolution failed.

### 6.5 IP Classification

Use `ipaddress` plus explicit checks.

Block by default:

- metadata:
  - `169.254.169.254`
  - `fd00:ec2::254` when parsed/available
  - hostnames resolving to metadata IPs
- loopback:
  - `127.0.0.0/8`
  - `::1`
- private:
  - `10.0.0.0/8`
  - `172.16.0.0/12`
  - `192.168.0.0/16`
  - IPv6 unique local `fc00::/7`
- link-local:
  - `169.254.0.0/16`
  - `fe80::/10`
- unspecified:
  - `0.0.0.0`
  - `::`
- multicast
- reserved
- carrier-grade NAT:
  - `100.64.0.0/10`
- documentation/test/benchmark special-use ranges:
  - `192.0.2.0/24`
  - `198.51.100.0/24`
  - `203.0.113.0/24`
  - `198.18.0.0/15`
- any non-global address in safe mode, unless a narrower explicit opt-in allows it.

Do not rely on `ip.is_private` alone. Python versions can differ on some special-use ranges. Keep explicit metadata, loopback, link-local, and unspecified checks.

### 6.6 Redirect And Proxy Behavior

Required:

- Create default production client with:
  - `httpx.Client(follow_redirects=False, trust_env=False)`
- Also pass `follow_redirects=False` at request time if supported by the current HTTPX version, so an injected client configured to follow redirects cannot bypass the initial URL check.
- Do not add support for auto-followed redirects in this issue.
- Add regression coverage that an allowed initial URL returning a 3xx to a blocked target does not trigger a second request.
- Add regression coverage that `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY` in the environment does not affect the default provider path.

Rationale:

- A redirect from an allowed public host to metadata/private IP is an SSRF bypass class.
- Environment proxies can silently change the egress route.

### 6.7 Local-Dev Opt-In

Safe mode must block localhost by default.

Local-first development needs an explicit escape hatch, but it must be operator-controlled. Do not let a scanned repo enable it by placing config in its own `pyproject.toml`.

Allowed sources:

- trusted Systograph app config
- explicit CLI flags
- explicit environment variables owned by the operator
- future UI toggle with clear confirmation

Disallowed as the sole source:

- scanned project `[tool.systograph.trace.security]`
- endpoint metadata generated from the scanned repo

Suggested local-dev behavior:

```toml
# Example only. Store in trusted Systograph/operator config, not untrusted scanned repo config.
[trace.security]
mode = "local-dev"
allow_loopback = true
allowed_hosts = ["localhost", "127.0.0.1", "::1"]
allowed_ports = [8000, 11434, 6333]
```

Rules:

- `mode="safe"`:
  - block loopback
  - block private
  - block link-local
  - block metadata
  - block unspecified
- `mode="local-dev"`:
  - only allow loopback when `allow_loopback=true`.
  - require host to be in `allowed_hosts`.
  - require port to be in `allowed_ports`.
  - still block metadata.
  - still block unspecified.
  - still block private network by default.
  - do not interpret local-dev as "allow all private network".

---

## 7. EndpointCallProvider Change Plan

### Files

- Modify: `src/systograph/core/providers/endpoint_call_provider.py`
- Create: `src/systograph/core/security/__init__.py`
- Create: `src/systograph/core/security/egress_policy.py`
- Create: `tests/unit/core/security/test_egress_policy.py`
- Modify/Create: `tests/unit/core/test_endpoint_call_provider.py`

### Step 1: Add `blocked_endpoint` Provider Status

Current:

```python
EndpointCallStatus = Literal[
    "ok",
    "timeout",
    "connection_error",
    "request_error",
    "http_error",
    "invalid_response",
    "unsupported_endpoint",
]
```

Add:

```python
"blocked_endpoint"
```

### Step 2: Inject Egress Policy

```python
class EndpointCallProvider:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        egress_policy: EgressPolicy | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            follow_redirects=False,
            trust_env=False,
        )
        self._egress_policy = egress_policy or EgressPolicy()
```

### Step 3: Evaluate Before `_request()`

Required order:

1. URL/scheme preflight.
2. Egress policy evaluation.
3. Return blocked result if denied.
4. Only then call `_request()`.

```python
preflight_result = self._endpoint_preflight_result(endpoint.value)
if preflight_result is not None:
    return preflight_result

egress_decision = self._egress_policy.evaluate(endpoint.value)
if not egress_decision.allowed:
    return EndpointCallResult(
        status="blocked_endpoint",
        query_sent=False,
        error_type="egress_policy_blocked",
        error_message=(
            "Endpoint blocked by query trace egress policy: "
            f"{egress_decision.reason}"
        ),
    )

response = self._request(...)
```

Do not include raw URL, credentials, query string, or request body in `error_message`.

### Step 4: Request-Level Redirect Hardening

Update `_request()` to pass `follow_redirects=False` when supported:

```python
self._client.request(
    method,
    url,
    params={"query": query},
    timeout=timeout_seconds,
    follow_redirects=False,
)
```

Same for JSON POST.

---

## 8. QueryTraceService, Web, And CLI Integration

### Files

- Modify: `src/systograph/core/services/query_trace_service.py`
- Modify: `src/systograph/web/routes/trace_routes.py` if route must pass trusted policy config.
- Modify: `src/systograph/cli/trace_command.py` if CLI supports local-dev policy flags.
- Modify: `src/systograph/core/services/query_trace_config_loader.py` only for trusted non-security trace config or if operator-owned config is clearly separated.

### Required Behavior

- If provider returns `blocked_endpoint` with `query_sent=false`:
  - `TraceRunResult.status` should remain `"partial"` unless schema is explicitly extended.
  - `TraceRunResult.query_sent` must be `false`.
  - `TraceRunResult.error_reason` should be `"egress_policy_blocked"`.
  - Events should be exactly one `error` event.
  - No `request_sent` event.

### Local-Dev Config Wiring

If local-dev is included in this PR, choose one of these safe wiring options:

1. **Operator config at app startup**
   - `create_app(query_trace_service=QueryTraceService(...))` gets a trusted policy config.
   - Web route does not trust scanned project `pyproject.toml` for security policy.

2. **CLI flags**
   - Add explicit flags such as:
     - `--trace-egress-mode local-dev`
     - `--allow-loopback-host localhost`
     - `--allow-loopback-port 11434`
   - Defaults stay safe.

3. **Environment variables**
   - Systograph-owned env vars, for example `SYSTOGRAPH_TRACE_EGRESS_MODE`.
   - Must be documented and tested.

Do not make scanned project config the only source of local-dev allowance.

---

## 9. Test Plan

### 9.1 Unit Tests For EgressPolicy

Create: `tests/unit/core/security/test_egress_policy.py`

Use fake resolver. Do not depend on real DNS or external network.

Cases:

- Missing scheme:
  - `example.com/api`
  - blocked as `unsupported_scheme` or `invalid_url`
- Unsupported schemes:
  - `file:///etc/passwd`
  - `gopher://127.0.0.1:6379`
  - `ftp://example.com/file`
- Missing hostname:
  - `http:///path`
- Userinfo rejected:
  - `http://user:pass@example.com`
  - `https://expected-host:fake@evil-host`
- Invalid port:
  - `http://example.com:99999/`
- Loopback IPv4:
  - `http://127.0.0.1:8000/api`
- Localhost via DNS:
  - `http://localhost:8000/api` resolves to `127.0.0.1` or `::1`
- IPv6 loopback:
  - `http://[::1]:8000/api`
- Private IPv4:
  - `http://10.0.0.5:8080/api`
  - `http://172.16.0.5:8080/api`
  - `http://172.31.255.255:8080/api`
  - `http://192.168.1.5:8080/api`
- IPv6 unique local:
  - `http://[fc00::1]/api`
- Link-local:
  - `http://169.254.1.1/api`
  - `http://[fe80::1]/api`
- Metadata:
  - `http://169.254.169.254/latest/meta-data/`
  - hostname resolving to `169.254.169.254`
- Unspecified:
  - `http://0.0.0.0:8000/api`
  - `http://[::]:8000/api`
- Multicast/reserved/non-global:
  - include at least one representative case.
- CGNAT and documentation/benchmark ranges:
  - `http://100.64.0.1/`
  - `http://192.0.2.1/`
  - `http://198.51.100.1/`
  - `http://203.0.113.1/`
  - `http://198.18.0.1/`
- IPv4-mapped IPv6:
  - `http://[::ffff:127.0.0.1]:8000/api`
- DNS resolve to private/loopback/metadata:
  - `evil.example.test -> 127.0.0.1`
  - `rebind.example.test -> 192.168.1.10`
  - `metadata.example.test -> 169.254.169.254`
- Allowed public endpoint:
  - `https://example.com/api -> 93.184.216.34`

### 9.2 Provider Regression Tests

Modify/Create: `tests/unit/core/test_endpoint_call_provider.py`

Required:

- Blocked endpoint returns:
  - `status == "blocked_endpoint"`
  - `query_sent is False`
  - `error_type == "egress_policy_blocked"`
- Blocked endpoint does not call HTTP client.
- Existing POST/GET happy-path tests still pass by injecting:
  - fake resolver that maps the test host to a safe public IP, or
  - an explicit allow policy stub for non-security provider tests.
- Unsupported scheme still returns `unsupported_endpoint` and does not call HTTP client.
- Invalid URL still returns `request_error` / `invalid_url` and does not call HTTP client.
- Redirect follow remains disabled, including a 3xx from an allowed URL to a blocked target.
- Default provider ignores proxy env vars through `trust_env=False`.
- If Track B is selected for DNS rebinding closure, add a test/harness proving the connect target is the same validated IP or that unsafe network egress is blocked below HTTPX.

Example no-call test:

```python
class FailingClient:
    def request(self, *args, **kwargs):
        raise AssertionError("HTTP client must not be called")


def test_blocked_endpoint_does_not_call_http_client() -> None:
    provider = EndpointCallProvider(
        client=FailingClient(),
        egress_policy=FakePolicy(block=True),
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:ssrf",
            value="http://127.0.0.1:8000/admin",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=1,
    )

    assert result.status == "blocked_endpoint"
    assert result.query_sent is False
    assert result.error_type == "egress_policy_blocked"
```

### 9.3 QueryTraceService Tests

Modify: `tests/unit/core/test_query_trace_service.py`

Add:

- `blocked_endpoint` provider result produces:
  - top-level `status == "partial"` unless schema is intentionally extended.
  - `query_sent is False`
  - no `request_sent` event
  - exactly one `error` event
  - `error.type == "egress_policy_blocked"`
  - `error_reason == "egress_policy_blocked"`

Keep:

- `endpoint_not_found` still does not call provider.
- `unsupported_endpoint` still does not emit `request_sent`.
- Timeout/transport errors with `query_sent=true` still keep `request_sent` plus `error`.

### 9.4 Web Route Tests

Modify: `tests/web/test_trace_routes.py`

Add:

- Route returns `query_sent=false` and no `request_sent` event when provider blocks.
- Invalid project trace config still returns `invalid_trace_config`.
- If local-dev is implemented, verify route does not accept untrusted scanned project config as the sole authority for egress allowance.

### 9.5 CLI Tests

Modify: `tests/cli/test_trace_command.py`

Add if CLI behavior changes:

- Safe mode blocks unsafe endpoints from a map JSON.
- CLI local-dev flags are explicit and default to safe mode.
- CLI output does not print raw URL credentials or raw query in blocked errors.

### 9.6 Config Loader Tests

Modify: `tests/unit/core/test_query_trace_config_loader.py` only if config loader is extended.

Required if security config is added:

- Trusted operator config parses mode, hosts, and ports.
- Invalid mode is rejected.
- Empty/duplicate hosts are rejected.
- Non-integer or out-of-range ports are rejected.
- Scanned project `pyproject.toml` cannot silently enable local-dev egress policy.

---

## 10. Documentation Plan

### Files

- Modify: `docs/API-GUIDE.md`
- Create: `docs/security/query-trace-egress-policy.md`
- Optionally modify: `docs/work/Timmy/schedule/plan/finish/22-implement-query-trace-mvp.md`

### Required Documentation Content

- Query trace is opt-in but endpoint values are still untrusted.
- Safe mode blocks localhost/private/link-local/metadata/unspecified/non-global destinations by default.
- Blocked endpoint semantics:
  - `query_sent=false`
  - no `request_sent` event
  - stable `error_reason="egress_policy_blocked"`
- Local-dev mode must be explicit and operator-controlled.
- Why scanned project config cannot be allowed to opt itself into localhost/private egress.
- Redirects are not followed.
- Default HTTPX client ignores proxy env vars with `trust_env=False`.
- DNS policy limitation:
  - resolve-before-request is a baseline guard.
  - full DNS rebinding protection requires pinned transport or network-layer controls.
- How to verify with focused tests.

---

## 11. Acceptance Criteria

Must pass:

- `http://127.0.0.1:*` is blocked in safe mode.
- `http://localhost:*` is blocked in safe mode.
- `http://10.x.x.x:*` is blocked.
- `http://172.16.x.x:*` through `http://172.31.x.x:*` is blocked.
- `http://192.168.x.x:*` is blocked.
- `http://169.254.169.254/*` is blocked.
- `http://169.254.x.x/*` is blocked.
- `http://[::1]:*` is blocked.
- `http://[fe80::1]/*` is blocked.
- `http://0.0.0.0:*` is blocked.
- `http://[::]:*` is blocked.
- Hostname resolving to private/loopback/link-local/metadata is blocked.
- DNS failure blocks before request.
- CGNAT, documentation, benchmark, reserved, multicast, and other non-global special-use ranges are blocked in safe mode.
- Blocked provider result:
  - `status="blocked_endpoint"`
  - `query_sent=false`
  - `error_type="egress_policy_blocked"`
  - no HTTP client call
- Query trace result for blocked endpoint:
  - `query_sent=false`
  - no `request_sent` event
  - stable error event and `error_reason`
- Allowed public endpoint can still be traced with a fake resolver/mock transport in tests.
- Local-dev mode, if implemented:
  - defaults off.
  - only allows explicit host plus explicit port.
  - does not allow arbitrary private network.
  - cannot be enabled solely by scanned project config.
- HTTPX default production client explicitly uses:
  - `follow_redirects=False`
  - `trust_env=False`
- Request calls explicitly keep redirect following disabled.
- Proxy environment variables do not change the default query trace egress route.
- DNS rebinding handling is clearly implemented as Track A or Track B; do not close as full DNS pinning if only Track A was implemented.
- API docs and security docs are updated.

---

## 12. Implementation Tasks

### Task 1: Lock Egress Policy Unit Tests

**Files:**

- Create: `tests/unit/core/security/test_egress_policy.py`

- [x] Add fake resolver abstraction for DNS tests.
- [x] Add URL parse/scheme/userinfo/port tests.
- [x] Add IP literal classification tests.
- [x] Add DNS resolution tests for public, loopback, private, link-local, metadata, and failure cases.
- [x] Add local-dev allowlist tests if local-dev is implemented.

### Task 2: Implement Egress Policy

**Files:**

- Create: `src/systograph/core/security/__init__.py`
- Create: `src/systograph/core/security/egress_policy.py`

- [x] Add `EgressPolicyConfig`, `EgressDecision`, `EgressBlockReason`.
- [x] Add `HostResolver` protocol and default socket resolver.
- [x] Implement URL parse and normalization.
- [x] Implement direct IP literal classification.
- [x] Implement DNS resolution and all-IP validation.
- [x] Implement safe mode default-deny for unsafe ranges.
- [x] Implement local-dev allowlist only if trusted config wiring is ready.
- [x] Ensure decisions do not include secrets or raw request bodies.
- [x] Choose Track A or Track B for DNS rebinding handling and document the chosen behavior in code comments/tests.
- [x] Track B is not selected; pinned-IP/network-layer enforcement remains documented residual work.

### Task 3: Connect EndpointCallProvider

**Files:**

- Modify: `src/systograph/core/providers/endpoint_call_provider.py`
- Modify: `tests/unit/core/test_endpoint_call_provider.py`

- [x] Add `blocked_endpoint` to `EndpointCallStatus`.
- [x] Inject `EgressPolicy`.
- [x] Create default `httpx.Client(follow_redirects=False, trust_env=False)`.
- [x] Run egress policy before `_request()`.
- [x] Return blocked result with `query_sent=false`.
- [x] Assert blocked endpoints do not call HTTP client.
- [x] Assert redirects are not followed to unsafe targets.
- [x] Assert default client ignores proxy env vars.
- [x] Preserve existing timeout/connection/http error behavior.
- [x] Preserve unsupported scheme behavior.
- [x] Update existing happy-path tests with fake resolver or allow policy stub.

### Task 4: Connect QueryTraceService Semantics

**Files:**

- Modify: `src/systograph/core/services/query_trace_service.py`
- Modify: `tests/unit/core/test_query_trace_service.py`

- [x] Add blocked endpoint service test.
- [x] Ensure blocked endpoint has no `request_sent` event.
- [x] Ensure top-level `query_sent=false`.
- [x] Ensure stable `error_reason="egress_policy_blocked"`.
- [x] Preserve timeout partial replay behavior.
- [x] Preserve endpoint-not-found no-provider-call behavior.

### Task 5: Align Web And CLI

**Files:**

- Modify: `src/systograph/web/routes/trace_routes.py` if policy config is passed per request.
- Modify: `src/systograph/cli/trace_command.py` if local-dev CLI flags are added.
- Modify: `tests/web/test_trace_routes.py`
- Modify: `tests/cli/test_trace_command.py` if CLI behavior changes.

- [x] Verify `/api/trace` uses the shared protected provider path.
- [x] Verify `systograph trace` uses the shared protected provider path.
- [x] Do not make scanned project config the sole authority for local-dev egress.
- [x] Keep trusted egress config separate; `QueryTraceConfigLoader` was not extended with security authority.
- [x] Add route/CLI regression tests when the user-facing contract changes.

### Task 6: Document Security Boundary

**Files:**

- Modify: `docs/API-GUIDE.md`
- Create: `docs/security/query-trace-egress-policy.md`
- Optionally modify: `docs/work/Timmy/schedule/plan/finish/22-implement-query-trace-mvp.md`

- [x] Document safe mode.
- [x] Document blocked response semantics.
- [x] Document local-dev opt-in and trusted config source.
- [x] Document redirect/proxy hardening.
- [x] Document DNS rebinding residual risk and future stronger mitigations.

---

## 13. Verification Commands

Run focused tests first:

```bash
.venv/bin/pytest tests/unit/core/security/test_egress_policy.py -v
.venv/bin/pytest tests/unit/core/test_endpoint_call_provider.py tests/unit/core/test_query_trace_service.py -v
.venv/bin/pytest tests/web/test_trace_routes.py tests/cli/test_trace_command.py -v
```

Run broader checks:

```bash
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/mypy src tests
git diff --check
```

If schema or generated docs change, also run the repo's schema/doc generation or validation command before closing the issue.

---

## 14. Suggested Commit Split

### Commit 1

```text
fix(security): add query trace egress policy
```

Content:

- `src/systograph/core/security/egress_policy.py`
- policy models
- resolver abstraction
- egress policy unit tests

### Commit 2

```text
fix(trace): block unsafe endpoint calls before request
```

Content:

- `EndpointCallProvider` policy integration
- `blocked_endpoint` provider status
- `follow_redirects=False`
- `trust_env=False`
- provider no-call regression tests

### Commit 3

```text
fix(trace): surface blocked egress as unsent trace result
```

Content:

- `QueryTraceService` blocked endpoint tests/semantics
- web/CLI alignment if needed

### Commit 4

```text
feat(trace): support explicit local-dev egress allowlist
```

Content only if implemented:

- trusted local-dev config source
- CLI/operator config wiring
- local-dev allowlist tests

### Commit 5

```text
docs(security): document query trace egress policy
```

Content:

- `docs/security/query-trace-egress-policy.md`
- `docs/API-GUIDE.md`
- limitations and future hardening

---

## 15. Conditions To Close #139

Only close #139 after all are true:

- Policy is connected to the actual query trace request path.
- Web and CLI query trace both use the protected provider path.
- Blocked endpoints do not send HTTP requests.
- Metadata/private/link-local/loopback/unspecified/DNS-to-unsafe regression tests pass.
- Safe mode blocks unsafe ranges by default.
- Any local-dev allowance is explicit, host-and-port scoped, and operator-controlled.
- Documentation explains why local-first does not mean "allow all localhost/private network".
- CI/focused validation passes.
- PR description lists:
  - threat model
  - changed files
  - blocked ranges
  - tests
  - remaining limitations, especially DNS TOCTOU if pinned transport is not implemented

---

## 16. Strict Reminder

Do not only check:

```python
actual_url == endpoint.value
```

That is not SSRF protection.

Correct baseline:

- endpoint_id must exist in the map
- URL parse
- scheme allowlist
- userinfo rejection
- hostname and port normalization
- DNS resolution
- all resolved IPs classified
- safe-mode egress deny policy
- explicit trusted local-dev allowlist
- redirect following disabled
- environment proxy disabled for default client
- block before request
- `query_sent=false`
- no HTTP client call

Document residual risk honestly:

- Without pinned-IP transport or network-layer egress restrictions, resolve-before-request does not fully eliminate DNS rebinding TOCTOU.

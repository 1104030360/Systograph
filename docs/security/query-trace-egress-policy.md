# Query Trace Egress Policy

## 安全目標

Query Trace 是使用者明確觸發的 runtime 功能，但 endpoint value 來自被掃描的 system map，因此仍必須視為不可信輸入。Systograph 在 `EndpointCallProvider` 這個共用 boundary 套用 egress policy，讓 Web `/api/trace` 與 CLI `systograph trace`（legacy alias：`kai-mind trace`）使用相同保護。

本實作採用 **Track A SSRF baseline**：

1. 解析 URL、scheme、userinfo、hostname 與 port。
2. 對 IP literal 直接分類；hostname 則先解析全部 IPv4/IPv6 結果。
3. 任一 DNS 結果不安全就阻擋整個 endpoint。
4. policy 通過後才允許 HTTP client 發 request。
5. 不跟隨 redirect，且預設不使用環境 proxy。

## Safe mode

Safe mode 是預設值，只允許所有解析結果皆為 global address 的 HTTP/HTTPS endpoint。

預設阻擋：

- AWS metadata address `169.254.169.254` 與已知 IPv6 metadata address
- IPv4/IPv6 loopback
- RFC1918 private network 與 IPv6 unique-local
- IPv4/IPv6 link-local
- unspecified address
- multicast、reserved 與其他 non-global special-use address
- CGNAT、documentation/test、benchmark ranges
- DNS 解析失敗或空結果
- URL userinfo、缺少 hostname、無效 port、非 HTTP/HTTPS scheme

Blocked provider result：

```json
{
  "status": "blocked_endpoint",
  "query_sent": false,
  "error_type": "egress_policy_blocked"
}
```

對外 `TraceRunResult` 維持既有 schema：

```json
{
  "status": "partial",
  "query_sent": false,
  "error_reason": "egress_policy_blocked",
  "events": [
    {
      "event_type": "error",
      "status": "blocked",
      "query_sent": false
    }
  ]
}
```

Blocked case 不會呼叫 HTTP client，也不會產生 `request_sent` event。

## Local-dev opt-in

Local-dev 不是「允許所有 private network」。它只允許 operator 明確指定的 loopback host 與 port，metadata、unspecified、link-local 與 arbitrary private network 仍然阻擋。

目前 Web app 可由可信任的 app startup 程式注入；被掃描專案的 `pyproject.toml` 沒有權限控制 egress policy：

```python
from kai_mind.core.providers.endpoint_call_provider import EndpointCallProvider
from kai_mind.core.security.egress_policy import (
    EgressPolicy,
    EgressPolicyConfig,
)
from kai_mind.core.services.query_trace_service import QueryTraceService
from kai_mind.web.app import create_app

policy = EgressPolicy(
    config=EgressPolicyConfig(
        mode="local-dev",
        allow_loopback=True,
        allowed_hosts=("localhost",),
        allowed_ports=(11434,),
    )
)
service = QueryTraceService(
    endpoint_call_provider=EndpointCallProvider(egress_policy=policy)
)
app = create_app(query_trace_service=service)
```

CLI 目前沒有 local-dev flag，固定使用 safe mode。若未來新增 CLI 或環境設定，來源必須是 Systograph operator-controlled config，不得讓 scanned project 自行放行 localhost/private egress。

## Redirect 與 proxy

- 預設 client 使用 `httpx.Client(follow_redirects=False, trust_env=False)`。
- 每次 request 也明確傳入 `follow_redirects=False`，避免 injected client 的預設值改變安全行為。
- 3xx response 會作為非成功 HTTP response 回傳，不會自動對 `Location` 再送第二次 request。
- `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 等環境設定不會改變預設 Query Trace egress route。

## DNS rebinding 限制

目前 policy 在 request 前解析 DNS 並檢查所有結果，可阻擋「hostname 當下解析到 private、loopback 或 metadata」的情況。

這不是完整 DNS pinning。HTTP transport 在 connect 階段可能再次解析 hostname，因此仍存在 time-of-check/time-of-use（TOCTOU）風險。若部署環境需要完整關閉 DNS rebinding，還必須採用其中一項：

- pinned-IP transport，確保實際 connect target 就是已驗證 IP；或
- network-layer egress deny，例如 firewall、VPC policy、Kubernetes NetworkPolicy。

在完成上述控制前，不得把本功能描述為 production-grade DNS rebinding closure。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/security/test_egress_policy.py -v
.venv/bin/pytest \
  tests/unit/core/test_endpoint_call_provider.py \
  tests/unit/core/test_query_trace_service.py -v
.venv/bin/pytest \
  tests/web/test_trace_routes.py \
  tests/cli/test_trace_command.py -v
```

## 參考資料

- OWASP SSRF Prevention Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- HTTPX redirects:
  https://www.python-httpx.org/compatibility/#redirects
- HTTPX environment variables:
  https://www.python-httpx.org/environment_variables/
- Python `ipaddress`:
  https://docs.python.org/3/library/ipaddress.html
- IANA IPv4 special-purpose registry:
  https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml
- IANA IPv6 special-purpose registry:
  https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml

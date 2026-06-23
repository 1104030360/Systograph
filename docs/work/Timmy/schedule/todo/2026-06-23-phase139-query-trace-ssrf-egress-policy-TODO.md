# Phase 139 Query Trace SSRF Egress Policy TODO

## 目標

在 Query Trace 真正送出 HTTP request 前，統一套用 SSRF egress policy，預設阻擋 metadata、loopback、private、link-local、unspecified、multicast、reserved 與其他 non-global 位址，並維持 Web 與 CLI 共用同一個安全邊界。

本次採用 **Track A baseline**：request 前解析 URL、DNS 與全部 IP 結果，停用 redirect 與環境 proxy。這能降低 DNS rebinding 風險，但不宣稱已完成 pinned-IP transport；剩餘 DNS TOCTOU 風險會寫入安全文件。

## 階段一：鎖定安全規則與測試案例

### 實作邏輯

- 將 egress policy 獨立放在 `core/security`，避免把安全規則散落在 Web route、CLI 或 service。
- 使用可注入的 resolver，讓測試不依賴真實 DNS 或外部網路。
- 使用 BDD 命名描述「Given 不可信 endpoint，When 執行 policy，Then 在 request 前阻擋」。

### 步驟

1. 建立 `tests/unit/core/security/test_egress_policy.py`。
2. 先涵蓋 URL scheme、userinfo、hostname、port 與 parse error。
3. 涵蓋 IPv4、IPv6、IPv4-mapped IPv6 與特殊用途網段。
4. 涵蓋 DNS 解析為 public、private、metadata、mixed result 與解析失敗。
5. 涵蓋 operator-controlled local-dev host + port allowlist。
6. 執行測試並確認因尚未有 production code 而正確失敗。

## 階段二：實作 EgressPolicy

### 實作邏輯

- Safe mode 採 default deny：只有所有解析結果皆為 global IP 才允許。
- Metadata、unspecified 等高風險位址即使在 local-dev 也不得放行。
- Local-dev 只允許明確 host、明確 port、明確 loopback；不等同允許任意 private network。
- 決策與錯誤訊息不包含 URL credentials、query string 或 request body。

### 步驟

1. 建立 `src/kai_mind/core/security/__init__.py`。
2. 建立 `egress_policy.py` 的 config、decision、reason 與 resolver abstraction。
3. 實作 URL normalization、port normalization、DNS resolve 與 IP classification。
4. 逐步執行單元測試完成 RED → GREEN → REFACTOR。

## 階段三：整合 EndpointCallProvider

### 實作邏輯

- `EndpointCallProvider` 是唯一強制 egress boundary。
- policy block 必須發生在 HTTP client 前。
- blocked result 固定為 `blocked_endpoint`、`query_sent=false`、`egress_policy_blocked`。
- 預設 HTTPX client 明確設定 `follow_redirects=False`、`trust_env=False`，request 層也明確不跟隨 redirect。

### 步驟

1. 先新增 provider blocked/no-call、redirect 與 client 設定測試。
2. 注入 `EgressPolicy`，現有非安全單元測試使用 allow stub。
3. 保留 timeout、transport、invalid URL、unsupported scheme 舊合約。
4. 執行 provider focused tests。

## 階段四：整合 QueryTraceService、Web 與 CLI

### 實作邏輯

- blocked endpoint 在 service 層仍維持既有 top-level `status="partial"`，避免破壞公開 schema。
- `query_sent=false` 時只產生一個 error event，不產生 `request_sent`。
- Web 與 CLI 不各自重做 policy，而是透過預設 `QueryTraceService → EndpointCallProvider` 共用保護。
- 被掃描專案的 `pyproject.toml` 只能控制 retrieved chunk keys，不能開啟 local-dev egress。

### 步驟

1. 先新增 service blocked semantics 測試。
2. 新增 Web route blocked response 測試。
3. 新增 CLI safe-mode blocked endpoint 測試。
4. 確認 static map/scan/viewer boundary 測試仍成立。

## 階段五：文件、驗收與回歸

### 實作邏輯

- API 文件說明 blocked contract 與安全預設。
- 安全文件說明 trusted local-dev 注入方式與 DNS TOCTOU 限制。
- 逐項對照 phase 139 acceptance criteria，不只以測試數量代替需求驗收。

### 步驟

1. 更新 `docs/API-GUIDE.md`。
2. 建立 `docs/security/query-trace-egress-policy.md`。
3. 每階段完成後建立 Report。
4. 執行 focused tests、全量 pytest、ruff、mypy 與 `git diff --check`。
5. 將完成計畫移至 `plan/finish`，並保留剩餘風險說明。

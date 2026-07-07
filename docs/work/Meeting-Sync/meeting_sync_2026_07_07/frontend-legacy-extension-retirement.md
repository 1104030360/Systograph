# 前端同步：v2 Compatibility 與 Legacy Extension 退役

Last updated: 2026-07-07（UA 整合決策對齊）

2026-07-07 UA 整合決策：本文件範圍不受影響；active v2 compatibility / legacy extension
retirement contract 不因 UA sidecar 新增 frontend 欄位。

## 目的（Purpose）

Plan `00A`、`13`、`15` 定義 migration path：

```text
00A: introduce ai-system-map/v2 compatibility migration
13: cut active output to v2 and retire active extension contract
14: validate real projects / fixtures / static execution artifacts
15: complete legacy v1 retirement only after compatibility gates pass
```

Frontend 不得跳過 compatibility migration。Active v2 retirement 僅在 backend
提供 samples 與 migration behavior 後進行。

## 目前 Contract 方向（Current Contract Direction）

Legacy v1 可能含 extension fields。Active v2 不應依賴 top-level `extensions`。

```text
legacy v1 artifact
  -> backend migration / adapter
  -> active v2 payload
  -> frontend renders active v2 payload
```

Frontend 不自行 migrate legacy extensions。

## Frontend 任務

### 1. Parser 就緒

Frontend 應能處理 active `ai-system-map/v2` payload，且不要求：

- top-level `extensions`；
- `ExtensionComponent`；
- `node:extension:*`；
- active `new_extension_component` happy path。

Compatibility 階段若 backend 仍提供 legacy-readable payload，frontend 應依 backend 提供的 active payload shape 渲染。

### 2. Mapping UI

Active CTA 應為 ambiguous evidence review，而非 extension creation。

Active UI 應移除的 legacy 文案：

```text
extension confirmation CTA
extension creation CTA
extension candidate as active happy path
```

僅在 backend 明確標為 legacy 時，才允許以唯讀 migration/legacy 註記顯示。

### 3. Graph UI

Active graph 不得建立 extension nodes。Capability overlays 應依 backend profile/projection contract 渲染。

若出現未經 backend migration 的 legacy payload，frontend 應以 contract warning 失敗，而非自行猜測轉換。

### 4. Detail / Trace

Active refs 應使用 backend 提供的 component、edge、evidence、profile、candidate 或 endpoint refs。不應有 active `extension` runtime ref type。

## 驗收標準（Acceptance Criteria）

- [ ] Active parser 不要求 top-level `extensions`。
- [ ] Active UI 不以 extension creation 作為 primary action。
- [ ] Frontend 不在本地 migrate legacy extensions。
- [ ] Active graph 不渲染 `node:extension:*`。
- [ ] Legacy extension data 若顯示，必須唯讀且標示 legacy。
- [ ] Plan `15` 視為 post-compatibility cleanup，而非立即 hard cut。

## 禁止事項（Do Not Do）

- 不要在 backend gate 通過前移除 compatibility handling。
- 不要建立 frontend-only extension replacements。
- 不要將 capability candidates 與 canonical graph nodes 混為一談。
- 不要在 `00A`、`13`、`14` 通過前將 `15` 描述為 hard cut。

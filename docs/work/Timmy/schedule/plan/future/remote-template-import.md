# Future: Remote Template Import

## 最新狀態校正（2026-06-12）

- 程式碼與計畫現況：Task 24 已完成的是 scan boundary review 與安全決策邊界；目前不應把 remote template import、template marketplace、template execution 或 external Git/URL import 拉回 EPIC1。現有 code path 仍以固定 `rag-core-v1` / local reference template 為主。
- 判斷：本項仍是 future，不應移到 `unfinish`。它需要 template provenance、schema versioning、digest/signature、migration policy、trust model 與 UI 管理流程，不是 EPIC1 收尾必備。
- 邊界提醒：未來若要做，也必須保持 template data-only，不執行任何 code，不下載 dependencies，不繞過 scanner read-only 與 local-only 安全限制。

## 來源
Task 3 (Create rag-core-v1 Reference Template) 在多處提到 remote template import 是最後才做的功能：

> scanner facts 必須映射到固定 slot，否則後面 `ComponentDetectionService`、flows、viewer graph 都沒有共同骨架。設計文件也明確要求 Epic 1 baseline 先固定 `rag-core-v1`，remote template import 最後才做。

> 不包含範圍：
> - 不做 template 商店。
> - 不做 remote repo import。
> - 不讓 template 執行任何 code。

Task 2 也提到：
> - 不處理 remote template schema。

## 目的
支援從外部來源（例如 Git repo、URL）匯入 reference architecture template，讓使用者可以使用非 `rag-core-v1` 的自訂 template。

## 觸發條件
- 使用者的 AI 系統不符合 `rag-core-v1` template（例如 agent-only、multimodal pipeline）。
- 需要支援社群或企業自訂的 reference architecture template。
- 需要 template 版本管理與更新機制。

## 設計約束
- Template 不可執行任何 code（不可有 hook、callback、script）。
- Remote template 必須經過 schema validation 後才能使用。
- 必須有 sandboxed import path，不可讓 template 存取 project 外的 filesystem。
- Import 過程不可引入 secret、executable、或未經驗證的 binary。

## 建議範圍
- 定義 template import protocol（URL / local path / Git ref）。
- 建立 template schema validation for imported templates。
- 建立 template store / registry（先 local，後 remote）。
- 支援 template 版本比對與 migration。

## 與既有任務關係
- Task 3：已建立 `RagTemplateService` 與 `rag-core-v1.json`。
- Task 24：final review 包含 template import 的 security boundary check。
- Task 19：manual mapping store 的 pattern 可參考。

## 不做事項
- 不建立 template marketplace / SaaS。
- 不讓 template 執行 code。
- 不自動下載或安裝 template 的 dependencies。

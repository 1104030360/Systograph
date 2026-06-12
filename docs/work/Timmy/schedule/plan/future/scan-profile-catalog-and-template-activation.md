# Future: Scan Profile Catalog and Template Activation

## 來源

本次 EPIC1 狀態校正（2026-06-12）檢查到：

- Task 24 已完成 backend scan boundary review 與 bounded scan policy。
- `24a` project mapping profile page 仍未完成，但比較像 EPIC2 的產品化管理介面。
- `remote-template-import.md` 仍應保留 future，不應提前變成 EPIC1 任務。

因此需要把「使用者如何選擇、檢視、啟用不同 scan profile / reference template」獨立成未來方向，避免混進 EPIC1 的 project scan UI 收尾工作。

## 目的

建立 scan profile / reference template 的 catalog、啟用與版本管理能力，讓 KAI-Mind 未來可以支援不同類型的 local AI 系統，而不只是一個固定的 `rag-core-v1` baseline。

## 為什麼不是 EPIC1 必做

EPIC1 的核心閉環應該是：

1. 使用本機專案路徑建立 project。
2. 做 bounded scan / boundary decision。
3. 產生 validated map artifact。
4. 前端能看 map、proposal、detail scan 與必要的 trace/evidence。

Scan profile catalog 是「多 profile 管理」與「模板治理」問題，不是單一 baseline readiness gate 必備能力。若太早做，會干擾 EPIC1 的收尾判斷，也會引入 provenance、migration、UI 管理與安全信任模型。

## 建議未來範圍

- 顯示目前可用的 scan profile / reference template。
- 支援 profile metadata：name、version、description、supported system type、schema version、digest。
- 支援啟用 / 停用 profile，但不得在 scan 過程執行任何 template code。
- 支援 profile compatibility check，避免用錯 template 掃錯系統類型。
- 支援 profile migration note，讓舊 scan result 可追溯當時使用的 profile。
- 與 project mapping profile page 整合，但不要把 profile catalog 當成 manual mapping overlay 的替代品。

## 不包含範圍

- 不做 remote marketplace。
- 不做 remote Git / URL template import；該方向仍屬 `remote-template-import.md`。
- 不讓 profile/template 執行 script、hook、postinstall、dependency download。
- 不把 profile catalog 當成 scanner canonical truth；canonical truth 仍是 validated `ai_system_map.json` artifact。

## 觸發條件

- EPIC1 baseline 完成後，需要支援非 `rag-core-v1` 的 AI 系統類型。
- 使用者需要在同一個 local app 裡比較不同 scan profile。
- 後續 EPIC2/EPIC3 需要把 mapping profile、template version、scan result lineage 串起來。

## 驗收標準草案

- 可列出本機可用 scan profiles。
- 可看見每個 profile 的版本、schema compatibility 與安全限制。
- 使用者選擇 profile 後，scan result artifact 能記錄 profile id/version/digest。
- profile 不可執行 code，且不可讓 scanner 掃出 local-only root 之外。
- 舊 scan result 可追溯當時使用的 profile。

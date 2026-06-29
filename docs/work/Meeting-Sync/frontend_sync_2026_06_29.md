# KAI-Mind Frontend 交接：Mapping Proposal Confirm / Reject（2026-06-29）

## 1. PR 範圍

- Base branch：`feature/detail-scan-ui-flow`
- Head branch：`feature/mapping-proposal-confirm-reject`
- Pull request：#199（stacked draft PR）
- 完成 issue：#85
- Backend dependencies：#41、#42（已完成並 merge）

本 PR 將 Viewer 中的 unmapped component 接到真實 Mapping Proposal API，
提供 proposal load/create、confirm、reject、loading、empty、error、retry 與成功狀態。

## 2. API wiring

Frontend 實際呼叫：

- `GET /api/mapping-proposals?project_id=...`
- `POST /api/mapping-proposals`
- `POST /api/mapping-proposals/{proposal_id}/decision`
- confirm 成功後重新讀取 `GET /api/map`

Frontend 不會自行修改 canonical map。Confirm 的 manual mapping 由 backend 建立；
Reject 不建立 manual mapping，元件維持 unknown。

## 3. UI 與資料安全

- Proposal modal 顯示 backend candidate、rationale、masked evidence references 與 uncertainty。
- Pending proposal 不會顯示為 confirmed fact。
- Confirm / reject 都有 busy、error 與 result state。
- Confirm 已成功但 map refresh 失敗時，UI 會保留成功結果並顯示 refresh warning。
- Sample mode 維持 mock/read-only seam；真實 API flow 只在有效 API project session 使用。
- 不顯示 raw source blob 或完整 secret。

## 4. 明確不在本 PR 的範圍

- #86 edit mapping proposal。
- `skip_for_now` action。
- `/api/mappings` direct manual-mapping CRUD UI。
- Scan Template page 的真實 backend persistence；該頁目前仍使用 mock service。

## 5. 主要修改檔案

- `frontend/src/components/proposal/ProposalModal.tsx`
- `frontend/src/components/proposal/CandidateCard.tsx`
- `frontend/src/hooks/useMappingProposal.ts`
- `frontend/src/services/mappingApi.ts`
- `frontend/src/types.ts`
- `frontend/src/App.tsx`

## 6. 驗證結果

```powershell
pnpm --dir frontend run lint
pnpm --dir frontend run build
uv run pytest tests/web/test_mapping_proposal_routes.py
```

結果：

- ESLint：0 errors；1 個既有 Fast Refresh warning。
- TypeScript / Vite production build：通過。
- Mapping Proposal route tests：`10 passed`。
- `git diff --check`：通過。
- 既有 build warnings：`web-worker` external dependency、bundle chunk 超過 500 kB。

## 7. Merge / rebase handoff

1. 先 merge PR #198。
2. 將 PR #199 base 改為 `main`，再 rebase 最新 `main`。
3. 確認 PR diff 只剩 Mapping Proposal 專屬修改與本文件。
4. 重跑本文件第 6 節的最小驗證。
5. Merge 後由 PR 關閉 #85；#86 保持開啟。


# Queue Board 轉換提案（2026-06-20）

這份文件是給 Timmy / Hardy 討論用的 Queue Board 整理提案。

目前尚未修改 GitHub Project #6 的任何欄位或 issue 狀態。這份文件只整理現況、問題、建議的新時間線欄位，以及初步遷移規則。

Project：

- GitHub Project #6：`Local-AI-Health-Doctor Execution`
- URL：https://github.com/users/1104030360/projects/6

## 1. 目前 Board 狀態

目前 Project 共有 96 個 items。

### Queue 分布

| Queue | Item 數 |
|---|---:|
| Now | 45 |
| Next | 19 |
| Later | 8 |
| Review | 6 |
| Roadmap | 8 |
| Tracking | 6 |
| Triage | 1 |
| Someday | 1 |
| 未填 Queue | 2 |

### Status 分布

| Status | Item 數 |
|---|---:|
| Todo | 88 |
| In progress | 7 |
| Done | 1 |

### Owner Lane 分布

| Owner Lane | Item 數 |
|---|---:|
| Timmy | 33 |
| Hardy | 31 |
| Shared | 30 |
| 未填 | 2 |

## 2. 目前主要問題

### 1. `Now` 過大

目前 `Now` 有 45 件，已經不像「現在要做」，比較像把 Fable findings 和前端 follow-up 全部倒進執行區。

這會造成：

- 每天打開 Board 時無法快速知道真正要做哪幾件。
- Current Iteration 失去承諾感。
- `Now` 和 backlog 的界線模糊。

### 2. `Current Iteration` 過大

目前 Current Iteration 有 38 件，幾乎都是 Timmy Fable findings。

建議 Current Iteration 只放這一輪真正承諾要推進的工作，而不是所有可能要處理的 finding。

### 3. Queue 分類過細

目前 Queue 包含：

```text
Roadmap
Next
Now
Review
Tracking
Later
Someday
Triage
```

其中 `Next`、`Later`、`Someday` 的差異在日常使用上偏細，容易讓分類成本高於實際價值。

### 4. `Triage` 不適合出現在主要時間線 Board

`Triage` 是「還沒判斷」，不是時間線狀態。

建議保留 `Triage` 作為欄位值或 Backlog Table 的暫存狀態，但不要放在主要 Queue Board view，避免破壞時間線。

### 5. 完成項目仍出現在 `Now`

例如：

- #137 `Polish scan template mapping UI copy and layout` 已 merged / Done，但仍在 `Now`。

完成項目如果還在 `Now`，會讓 Board 看起來比實際更擁擠。

### 6. 新 issue 未分類

目前有 2 件未填 Queue / Owner / Priority / Work Area / Work Type：

- #185 `Add evidence code preview drawer for scan template mappings`
- #187 `Track frontend Vite build warnings`

這兩件應先分類，否則會在 Backlog Table 裡漂著。

## 3. 建議的新 Queue Board 時間線

建議主要 Queue Board 改成：

```text
Planned -> Now -> Review -> Resolved | Tracking
```

也就是主 Board 只保留 5 欄：

| Queue | 意思 | 是否是時間線 |
|---|---|---|
| Planned | 確定未來會做，但不是現在 | 是 |
| Now | 正在做，或這一輪明確承諾要推進 | 是 |
| Review | 已完成實作，等待 review / merge / close decision | 是 |
| Resolved | 已 merge、已 close、duplicate、wontfix、superseded | 是 |
| Tracking | Epic、Parent、umbrella issue、長期追蹤項 | 否 |

### 不建議在主要 Board 顯示

| Queue | 建議處理 |
|---|---|
| Triage | 保留在 Backlog Table，不放主要 Board |
| Someday | 併入 Planned，或移出 Project |
| Later | 併入 Planned |
| Next | 併入 Planned |
| Roadmap | 併入 Tracking |

## 4. 欄位語意建議

### Planned

放確定會做的工作，不要求本週完成。

適合放：

- 已確認的 frontend/backend integration task。
- Fable findings 中尚未進入本輪處理的項目。
- Post Epic 1 但明確會做的項目。

不適合放：

- 還沒看懂的 issue。
- Epic / Parent。
- 已完成或已 merge 的項目。

### Now

放目前真正正在做的工作。

建議限制：

```text
Now 最多 3-5 件。
```

適合放：

- 已經有人正在開 branch。
- 本輪明確承諾要完成。
- P0 / P1 且已確認優先序。

### Review

放等待 review / merge / close decision 的工作。

適合放：

- Open PR。
- 已 merge 但需要確認是否可以 close 對應 issue。
- 實作完成但需要 UI / product 驗收。

### Resolved

放已處理完、不需要再推進的項目。

適合放：

- PR merged。
- Issue closed。
- Duplicate / superseded / wontfix。
- 已確認由其他 issue 或 PR 覆蓋。

建議保留 1-2 週後，可以從 Project 移除，避免 Board 永久變胖。

### Tracking

放不直接執行的脈絡項目。

適合放：

- Epic。
- Parent issue。
- Umbrella / milestone tracking issue。

不適合放：

- 可以直接開 branch 做的小 issue。

## 5. 舊 Queue 到新 Queue 的遷移規則

| 舊 Queue | 新 Queue 建議 |
|---|---|
| Roadmap | Tracking |
| Tracking | Tracking |
| Next | Planned |
| Later | Planned |
| Someday | Planned 或移出 Project |
| Triage | 不顯示在主要 Board；先留 Backlog Table |
| Now | 重新判斷：少數留 Now，多數移 Planned |
| Review | Review 或 Resolved |
| 未填 Queue | 先補欄位，再放 Planned / Review / Resolved |

## 6. 初步 item 遷移建議

### A. 建議留在 Now

目前只建議保留真正正在處理或最高優先的少數項目。

| Issue | 建議 |
|---|---|
| #138 `[Security][Critical][C-1] fix: prevent unmasked credentials in system map outputs` | 留在 Now，P0 且 In progress |

可由 Timmy 再決定是否把 #139-#145 中 1-2 件拉進 Now。

### B. 建議從 Now 移到 Planned

目前 `Now` 中大多數 Fable findings 應移到 Planned，等真正要做時再拉進 Now。

建議移到 Planned：

```text
#139-#145 High findings
#146-#175 Medium / Low backend-security-contract findings
#176-#181 Frontend findings
```

例外：

- 如果 Timmy 已經明確本週要做其中幾件，可以保留在 Now。
- 如果 Hardy 下一步要做 frontend API integration，可把相關 frontend item 留在 Now 或排 Planned 前段。

### C. 建議 Review / Resolved decision

| Issue / PR | 目前狀態 | 建議 |
|---|---|---|
| #137 | Merged / Done，但仍在 Now | 移到 Resolved |
| #131-#136 | Open / In progress / Review | 由 Hardy 檢查是否已由 #137 / #186 覆蓋；能 close 的 close，剩下移 Planned 或 Review |
| #186 | Merged | 若在 Project 中出現，放 Resolved |

### D. 建議補欄位的新 issue

| Issue | 建議 Queue | Owner | Priority | Work Area | Work Type | 備註 |
|---|---|---|---|---|---|---|
| #185 Evidence code preview drawer | Planned | Shared 或 Hardy | P2 | Frontend 或 Contract | Feature | 需要前後端串接 branch，可能牽涉 API contract |
| #187 Vite build warnings | Resolved 或 Planned | Hardy | P2 | Frontend | Performance | 可能與 #181 重複，建議併入 #181 |

### E. 建議 Tracking

目前 `Roadmap` 的 Epic 和 `Tracking` 的 Parent 都可放到 `Tracking`：

```text
#1-#8 Epic
#53-#58 Parent frontend task trackers
```

如果想保留 Epic 與 Parent 的視覺差異，可在 Tracking view 裡用 Work Type 分組，而不是分成 Roadmap / Tracking 兩個 Queue。

### F. 建議 Planned

目前 `Next` 和 `Later` 大多可直接轉 Planned：

```text
#74-#92 Frontend Epic 1 phase tasks
#122 Project scan and boundary decision flow
#123-#127 Post Epic 1 feature work
#130 Worker queue / distributed system research
```

### G. 建議移出主要 Board 或留 Backlog Table

| Issue | 建議 |
|---|---|
| #124 OpenAPI generated frontend SDK | 如果確定會做，移 Planned；如果還沒決定，留 Backlog Table / Triage，不顯示在主要 Board |
| #128 Page-aware RAG assistant | 若仍是遠期想法，移 Planned 後排很後，或直接移出 Project 保留 issue |

## 7. 建議的 Board View 設定

主要 Queue Board view：

```text
Filter:
Queue is Planned OR Now OR Review OR Resolved OR Tracking

Group by:
Queue

Sort:
Manual / Rank
```

Backlog Table view：

```text
顯示所有 items
包含 Queue 為空、Triage、Someday、Later 等未整理項
用來做週期性整理，不作日常執行視圖
```

Current Iteration view：

```text
只放本輪確定要完成或推進的 item
建議 5-10 件以內
不要把整批 Fable findings 全部放進 current iteration
```

## 8. 建議執行步驟

建議分兩階段，不要一次搬完。

### Phase 1：欄位與視圖調整

1. 新增 Queue options：
   - `Planned`
   - `Resolved`
2. 更新 Queue Board view，只顯示：
   - Planned
   - Now
   - Review
   - Resolved
   - Tracking
3. 保留 Backlog Table 顯示所有項目。

### Phase 2：item 搬遷

1. #137 移到 Resolved。
2. #185、#187 補欄位。
3. `Next` / `Later` 批次移到 Planned。
4. `Roadmap` 批次移到 Tracking。
5. `Now` 中只保留 #138 和 Timmy 指定的少數本輪工作。
6. #131-#136 由 Hardy / Timmy 確認是否 close 或移 Resolved。
7. Current Iteration 從 38 件縮到真正本輪承諾項目。

## 9. 需要 Timmy 決定的問題

1. 是否同意主要 Queue Board 改成時間線：

```text
Planned -> Now -> Review -> Resolved | Tracking
```

2. 是否同意 `Triage` 不出現在主要 Board，只留 Backlog Table。

3. 是否同意 `Roadmap` 併入 `Tracking`，用 Work Type 區分 Epic / Parent。

4. Fable findings #139-#175 中，Timmy 本輪真正要留在 Now 的項目是哪幾件？

5. #187 是否關成 #181 的 duplicate，或保留成獨立 build hygiene issue？

6. #131-#136 是否已被 #137 / #186 覆蓋，可以逐一 close？

## 10. 建議結論

建議採用新的時間線式 Queue Board：

```text
Planned -> Now -> Review -> Resolved | Tracking
```

這樣 Board 會從「分類很多的 issue 倉庫」變成「每天能看懂的工作流」。

最重要的改變不是新增欄位，而是重新定義 `Now`：

```text
Now 只放真的正在做或本輪承諾要做的少數項目。
```

其餘確定會做但不是現在的工作，統一放 `Planned`。Epic / Parent 統一放 `Tracking`。已處理完的放 `Resolved`，短期保留後可定期從 Project 移除。

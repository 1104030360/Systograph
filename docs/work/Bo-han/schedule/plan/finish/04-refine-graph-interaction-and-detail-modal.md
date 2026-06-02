# Task 4: Refine Graph Interaction and Detail Modal

## 目標

改善 Viewer 的互動體驗：node / edge detail 改為 modal、右側保留 local model
chat 區域、edge routing 與 Follow focus 可用。

## 為什麼要做這個

右側 panel 未來會放 local model chat，不適合長期作為 node detail inspector。
同時 graph 若線條重疊或播放閃動，會讓使用者無法理解資料流。

## 實作範圍

- Detail modal。
- L1 / L2 / L3 segmented detail view。
- Local model chat placeholder。
- Edge sequence pills。
- Edge lane routing。
- Follow focus toggle。
- Replay / progress 不重新 layout。
- Responsive replay panel。

## 不包含範圍

- 不實作真正 local model chat。
- 不實作 L2 / L3 backend detail scan。
- 不實作 Playwright regression tests。

## 建議實作步驟

1. 將 `DetailPanel` 從右側 aside 改為 modal。
2. 新增 `ChatPanel` placeholder。
3. 移除 replay 時的 edge animation 與重複 layout。
4. 新增 edge ordered pill，長 relationship 放 detail modal。
5. 新增 Follow focus state 與 toolbar button。
6. 將 edge routing 改成 x/y lane offset。
7. 壓縮 replay panel 高度並處理窄寬度。

## 預期輸出

- `frontend/src/components/DetailPanel.tsx`
- `frontend/src/components/ChatPanel.tsx`
- `frontend/src/components/SystemGraph.tsx`
- `frontend/src/store/viewerStore.ts`
- `frontend/src/styles.css`

## 驗收標準

- 點 node / edge 會開 detail modal。
- 右側固定顯示 chat placeholder。
- 勾選 Highlight 並播放 replay 時不再閃動。
- Follow 開啟時可置中目前 node，關閉時不自動移動。
- 多分支 edge 不完全重疊。

## 可能風險與注意事項

- Follow target 不可被 filter highlight 誤導。
- Edge target 是 edge id 時，要轉成 target node 才能置中。
- Edge lane routing 若資料量增加，仍可能需要更完整的 collision avoidance。

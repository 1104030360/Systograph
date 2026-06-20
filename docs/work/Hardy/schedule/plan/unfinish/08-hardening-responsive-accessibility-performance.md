# Task 8: Harden Responsive Layout, Accessibility, and Performance

## 目標

收斂 Viewer 的響應式版面、鍵盤可用性、可讀性與大圖效能，讓 Epic 1 Viewer
從 prototype 進入可 review 的產品品質。

## 實作範圍

- 窄寬度 layout。
- Replay timeline density。
- Toolbar wrap。
- Modal focus / escape close。
- Icon button aria-label。
- 大 graph chunk / code splitting 評估。
- Edge label / lane collision refinement。

## 不包含範圍

- 不做完整 design system。
- 不做 mobile-first 產品化。
- 不做雲端部署。

## 建議實作步驟

1. 用 1440、1280、980 viewport 手動檢查。
2. 補 modal keyboard close。
3. 補 toolbar / chat / replay 的 accessible labels。
4. 檢查 build chunk warning，評估是否拆 graph vendor chunk。
5. 針對大型 graph 補 viewport defaults 與 minimap 行為。

## 驗收標準

- 主要文字不重疊。
- toolbar 在較窄寬度不溢出。
- replay timeline 不擠壓成不可讀。
- modal 可用鍵盤關閉。
- build 警告有明確後續處理策略。

# Phase 1：重新定位與 UI 骨架

**預估時間：** 1 週  
**前置條件：** Phase 0 完成

**目的：** 把 KAI-Mind 從「文件聊天工具」重新定位成「Local AI Health Doctor」，建立診斷 dashboard 的 UI 骨架。

---

## 🎯 核心目標

> 使用者一進入專案就知道：這不是文件聊天工具，而是 local AI diagnostics tool。

---

## ✅ Checklist

### 1.1 專案定位更新

- [ ] 更新 `README.md` 標題與簡介為 "Local AI Health Doctor"
- [ ] 更新 one-liner 描述（中英文）
- [ ] 更新 repo description（GitHub）
- [ ] 更新 `package.json` / `pyproject.toml` 的 description 欄位

### 1.2 UI 骨架 — Dashboard 首頁

- [ ] 設計並實作診斷 dashboard 首頁
- [ ] 首頁要有 5 個模組的入口卡片：
  - Environment Scanner
  - Model Fit Advisor
  - Performance Benchmark
  - Privacy / Security Guard
  - RAG Quality Inspector
- [ ] 每個卡片顯示模組名稱、簡述、狀態指示（尚未掃描 / 健康 / 警告）
- [ ] dashboard 整體風格要傳達「診斷工具 / 健檢報告」的感覺

### 1.3 UI 骨架 — 5 個模組頁面

- [ ] 建立 Environment 頁面骨架（空白 placeholder）
- [ ] 建立 Model Fit 頁面骨架
- [ ] 建立 Performance 頁面骨架
- [ ] 建立 Privacy 頁面骨架
- [ ] 建立 RAG Quality 頁面骨架
- [ ] 確認所有頁面可以從 dashboard 正確導航

### 1.4 保留原有功能

- [ ] 確認原本的 KAI-Mind local RAG engine 仍然可運行
- [ ] 將原本的文件上傳 / RAG 問答功能保留（後續轉為 RAG Quality Inspector 的輸入）
- [ ] 不要在這個 Phase 刪除任何核心功能

### 1.5 路由與導航

- [ ] 設定前端路由（各模組頁面都有獨立 URL）
- [ ] 建立側邊欄或 top navbar 導航
- [ ] 加入 breadcrumb 或標題讓使用者知道自己在哪

---

## 📌 完成標準

- [ ] 打開首頁看到的是「診斷 dashboard」，不是聊天介面
- [ ] 5 個模組頁面都能正確進入
- [ ] 原本的 RAG 功能仍然可用
- [ ] UI 風格傳達出「健檢 / 診斷工具」的定位

---

## ➡️ 下一步

完成後前往 → [Phase 2：Environment Scanner](./phase-2-environment-scanner.md)

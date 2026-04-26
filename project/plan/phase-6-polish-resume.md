# Phase 6：工程品質與履歷包裝

**預估時間：** 1–2 週  
**前置條件：** Phase 5 完成

**目的：** 把專案的工程品質拉到「可以放進履歷、能支撐面試故事」的水準。

---

## 🎯 核心目標

> 專案可以放進履歷，並且能支撐面試故事。面試官看到 GitHub 會覺得：這個人工程素養很扎實。

---

## ✅ Checklist

### 6.1 CI/CD — GitHub Actions

- [ ] 設定 GitHub Actions workflow
- [ ] PR 時自動跑 lint
- [ ] PR 時自動跑 pytest
- [ ] PR 時自動跑 build
- [ ] 加入 status badge 到 README

### 6.2 測試覆蓋

- [ ] 確認所有模組都有基本測試
- [ ] 補齊重要的 edge case 測試
- [ ] 確認 `pytest` 全部通過
- [ ] （可選）加入 coverage report

### 6.3 安全掃描

- [ ] 設定 CodeQL 或 Dependabot
- [ ] 確認沒有已知的安全漏洞

### 6.4 Docker

- [ ] 確認 `docker-compose.yml` 能一鍵啟動所有服務
- [ ] 確認 Dockerfile 是乾淨的、層數合理
- [ ] 寫好 Docker 啟動文件

### 6.5 文件

- [ ] README 加入 architecture diagram（Mermaid 或圖片）
- [ ] README 加入 features 列表
- [ ] README 加入 demo GIF 或 screenshot
- [ ] 寫 API documentation（各 endpoint 的 request/response 格式）
- [ ] 產出一份 sample diagnosis report（給面試官看的範例輸出）

### 6.6 Demo

- [ ] 錄製 demo video（3–5 分鐘）
- [ ] 展示完整流程：啟動 → 掃描 → 推薦 → benchmark → privacy → RAG quality → 匯出
- [ ] 放到 README 或 YouTube

### 6.7 專案管理

- [ ] 整理 GitHub Issues（把未來 TODO 寫成 issue）
- [ ] 建立 roadmap（可用 GitHub Projects 或 README 中的 roadmap section）
- [ ] 加入 LICENSE
- [ ] 確認所有 commit message 清楚

---

## 📌 完成標準

- [ ] GitHub Actions badge 是綠色的
- [ ] `pytest` 全部通過
- [ ] `docker-compose up` 能正常啟動
- [ ] README 有 architecture diagram + demo + 清楚說明
- [ ] 有 API documentation
- [ ] 有 demo video
- [ ] 面試時能花 3 分鐘清楚講完這個專案的價值與技術細節

---

## 🎉 恭喜完成！

走到這一步，你的 KAI-Mind — Local AI Health Doctor 已經是一個完整的、可展示的、面試可講的專案了。

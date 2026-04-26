# Backend Architecture Documentation

本資料夾整理 IT Ticket System 後端架構、資料流、可視化圖表、程式碼審查結論與重構路線。文件依據目前程式碼與以下審查規則產出：

- `.cursor/rules/linux_torvalds_code_review.mdc`
- `.cursor/rules/linus_torvalds.mdc`

## 建議閱讀順序

1. `backend-architecture-overview.md`
   - 先看系統入口、技術棧、目錄分工、資料儲存與外部整合。
2. `backend-architecture-diagrams.md`
   - 用 Mermaid 圖快速掌握模組依賴、API lifecycle、資料流與 ERD。
3. `backend-code-review.md`
   - 看依審查規則得到的評分、證據、風險與改善建議。
4. `backend-refactor-roadmap.md`
   - 看 Critical、High、Medium、Low 的重構優先順序與階段目標。

## 維護方式

- 後端入口、API route、service、repository 或資料儲存格式改動時，更新 overview 與 diagrams。
- 新增認證、背景工作、CI/CD 或部署方式時，同步更新 code review 與 roadmap。
- 每次大型重構後重新跑測試與覆蓋率，再更新測試狀態描述。
- Mermaid 圖表請維持在 Markdown code block 中，方便 Git diff 與文件預覽。


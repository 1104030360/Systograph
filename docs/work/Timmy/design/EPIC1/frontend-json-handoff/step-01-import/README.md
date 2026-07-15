# Step 1 — 輸入 / Import

Last updated: 2026-07-15（current runtime）

Current endpoint 是 `POST /api/projects/import`。Backend 將 local project 登記到 project
registry，回傳 `project_id`、`source_type`、`project_name`、`project_path` 與 `reused`。

本步沒有獨立 handoff sample；frontend 只保留 import response，之後以 `project_id` 啟動
Step 2。`project.json` 是 backend state，不是 frontend contract。Frontend 不應把 local
absolute path 寫進 telemetry、錯誤回報或其他 public artifact。

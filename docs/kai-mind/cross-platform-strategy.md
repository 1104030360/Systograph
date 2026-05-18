# 跨平台架構策略

## 決策

不要把 KAI-Mind 做成 Windows-only `.exe`。

產品應該以共用的 Core Engine 與 CLI 為中心。Windows `.exe`、macOS app、Local Web UI 與 CI integration 都應該呼叫同一份 core behavior。

## 建議架構

```text
KAI-Mind
+-- Core Engine
|   +-- scanners
|   +-- checkers
|   +-- risk engine
|   +-- report generator
+-- CLI
|   +-- kai-mind scan
|   +-- kai-mind gate --ci
+-- Local Backend
|   +-- exposes scan/report APIs to localhost
+-- Local Web UI
|   +-- dashboard for selecting project folder and viewing report
+-- Platform Launchers
    +-- Windows: .exe
    +-- macOS: .app / .dmg
    +-- Linux: binary or AppImage
```

## 為什麼 Local Web UI 不會影響資料讀取

純 browser app 沒辦法安全且穩定地掃描本機 project folders、`.env`、Docker state、ports 與 running services，因為瀏覽器的 filesystem access 受到限制。

Local Web UI 則不同：

- UI 在 `localhost` 的 browser 中執行。
- 實際掃描由 local backend 或 CLI 執行。
- Scanner 只讀取使用者選擇的 folder 或明確設定的 target。
- Reports 預設在本機產生。

因此，從 `.exe only` 改成 Local Web UI 不會削弱 scanner 能力。它只是讓產品更跨平台，同時保留 local-first 的資料處理方式。

## MVP 建議技術

- Core / CLI：Python
- Local API：FastAPI
- Web UI：React 或其他輕量 frontend
- 後續 packaging：Tauri 或 Electron launcher
- CI：GitHub Actions 呼叫 CLI

## Guardrails

- Scanners 預設必須 read-only。
- 不顯示完整 secret values。
- Network checks 應該是 shallow checks，並說明不確定性。
- `0.0.0.0` 應回報為 possible exposure，不應直接等同於 internet exposure。
- Launcher code 要保持薄，不要在 platform-specific packages 中重複 scanner logic。

## 實務團隊流程

Windows 與 macOS 開發者都應該可以執行：

```bash
kai-mind scan --project ./sample-ai-stack --output report.json
kai-mind gate --ci
```

Launcher 只是 convenience。CLI 才是真正穩定的 contract。

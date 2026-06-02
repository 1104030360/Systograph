# Future: Dependency Manifest Advanced Formats and Lockfiles

## 來源
Task 10 (Implement Dependency Manifest Provider) 在「不包含範圍」和「建議實作步驟」中提到多項延後的能力：

> 不包含範圍：
> - 不建立完整 SBOM。
> - 不執行 package manager。
> - 不下載 dependency。
> - 不做 vulnerability scan。

> `requirements.txt` parser 中，`-r` include、editable install、VCS URL 先記成 unsupported / parse issue，不遞迴讀檔、不連網。

> 參考依據：Syft SBOM docs 可作 dependency inventory 設計參考，但 Epic 1 不直接整合 Syft。

## 目的
擴充 `DependencyManifestProvider` 支援更多 manifest 格式、lockfile 解析、以及進階 requirements 語法。

## 觸發條件
- 使用者的專案使用 lockfile（例如 `uv.lock`、`poetry.lock`、`package-lock.json`、`yarn.lock`、`pnpm-lock.yaml`）作為 dependency 來源。
- 使用者的 `requirements.txt` 使用 `-r` recursive include、editable install、VCS URL 等進階語法。
- 需要支援 `go.mod`、`Cargo.toml` 等非 Python/Node manifest。
- 需要整合 lightweight SBOM output。
- 需要 vulnerability awareness（例如與 osv.dev 或 pip-audit 結合）。

## Future 1: Lockfile 解析
- 支援 `uv.lock`、`poetry.lock`、`package-lock.json`、`yarn.lock`、`pnpm-lock.yaml`。
- Lockfile 可提供 exact installed version，比 manifest 的 version range 更精確。
- 只做 static parse，不執行 package manager。

## Future 2: requirements.txt 進階語法
- 支援 `-r` recursive include（在 `FileInventory` 邊界內遞迴）。
- 支援 editable install（`-e`）的 package name extraction。
- 支援 VCS URL（`git+https://...`）的 package name extraction。
- 支援 constraint files（`-c`）。

## Future 3: 更多語言的 manifest
- `go.mod` / `go.sum`
- `Cargo.toml` / `Cargo.lock`
- `Gemfile` / `Gemfile.lock`
- `build.gradle` / `pom.xml`

## Future 4: Lightweight SBOM Output
- 參考 Syft 的 SBOM 格式（CycloneDX / SPDX）。
- 只輸出 declared dependency，不做完整 installed package inventory。
- 作為 readiness report 的附加資訊。

## Future 5: Vulnerability Awareness
- 整合 osv.dev API 或 pip-audit 的 vulnerability database。
- 只產生 risk hint，不做完整 vulnerability scan。
- 需要 network access（opt-in，不預設啟用）。

## 與既有任務關係
- Task 10：已建立 `DependencyManifestProvider` 基礎 parser。
- Task 12a：rule catalog 可擴充 manifest rules。
- Task 14：vulnerability hint 可作為 risk hint 來源。
- Task 23：hardening 階段可驗證 lockfile parse 安全性。

## 不做事項
- 不執行 package manager。
- 不下載 dependency。
- 不做 runtime installed package scan（Syft 的完整能力）。
- 不做 license compliance scan。

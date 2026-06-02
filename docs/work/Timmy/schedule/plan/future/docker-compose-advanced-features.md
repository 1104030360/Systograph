# Future: Docker Compose Advanced Features

## 來源
Task 9 (Implement Docker Compose Provider) 提到多項初版不處理的 Compose 進階功能：

> 不包含範圍：
> - 不啟動 Docker。
> - 不執行 `docker compose`。
> - 不做完整 network security scan。

> `env_file` 先當成 service-level reference fact；若要讀 env file 內容，只能讀 `FileInventory` 已納入且仍在 project root 內的 eligible file，不可因 compose path 重新擴張掃描邊界。

> `depends_on` 可能是 list short form 或 map long form；第一版只需要 normalize 出 dependency service names，不解讀健康檢查語意。

> published port 只是 network exposure hint，不等於已證明公開暴露。

> 不做 Compose interpolation / merge / profile evaluation。
> 對 unsupported 或 ambiguous Compose feature 保留原始 masked reference 與 uncertainty，不猜測 runtime final state。

## 目的
擴充 `DockerComposeProvider` 支援更完整的 Compose spec 解析。

## 目前狀態（2026-06-02）
這份仍屬 future plan，但 Task 9 已完成部分基礎 Compose parsing。不要把下列項目誤判成尚未開始：

已完成基礎能力：
- `services.*.image` 會產生 service image facts，並對 Qdrant / Ollama / pgvector image 給出專用 rule id。
- `ports` 已支援 short syntax 與 object long syntax，會產生 `published_port` facts。
- `environment` 已支援 map 與 list syntax，value 會通過 secret masking。
- `env_file` 已支援 string / list / object `{path: ...}`，但只輸出 service-level reference fact，不讀 env file 內容。
- `volumes` 已支援 string syntax 與 object long syntax，會產生 volume facts。
- `depends_on` 已支援 list short form 與 map long form，但只 normalize dependency service names，不解讀 `condition` / healthcheck 語意。

仍屬 future：
- Compose variable interpolation。
- multiple Compose files merge / override。
- Compose profiles。
- `depends_on.condition` health semantics。
- 讀取 `env_file` 內容並合併 config facts。
- network exposure 深度分析。
- `docker compose config` / Docker daemon runtime evaluation 仍不應做。

## 觸發條件
- 使用者的 Compose 使用 variable interpolation（`${VAR}`），scanner 無法產生完整 evidence。
- 使用者使用 multiple Compose files merge / override。
- 使用者使用 Compose profiles。
- 需要更精準的 network exposure analysis（不只是 published port hint）。

## Future 1: Compose Variable Interpolation
- 支援 `${VAR:-default}` 語法。
- 只做 static 解析（用 `.env` file + inline default），不執行 shell。
- 記錄 unresolved variable 為 uncertainty evidence。

## Future 2: Multiple Compose Files Merge
- 支援 `docker compose -f a.yml -f b.yml` 的 merge 行為。
- 遵守 Compose spec 的 merge rules。

## Future 3: Compose Profiles
- 支援 `profiles` field，辨識哪些 service 只在特定 profile 啟用。
- 對 profile-only service 產生 conditional evidence。

## Future 4: depends_on 健康檢查語意
- 解讀 `depends_on` long form 的 `condition` 欄位。
- 辨識 service startup order 與 health dependency。
- 注意：Task 9 已完成 dependency service names normalization；本 future 只處理 `condition` / healthcheck 語意，不是重新做 depends_on 基礎解析。

## Future 5: env_file 內容讀取
- 在 `FileInventory` 邊界內讀取 `env_file` 指向的檔案。
- 合併 env_file 與 inline environment 的 config facts。
- 不可因 compose path 擴張掃描邊界。
- 注意：Task 9 已完成 env_file reference fact；本 future 只處理「讀內容並合併 config facts」。

## Future 6: Network Exposure 深度分析
- 結合 `networks` 定義分析 service 間通訊。
- 區分 internal network 與 external exposed port。
- 產生更精準的 network exposure risk hint。

## 與既有任務關係
- Task 9：已建立 `DockerComposeProvider` 基礎 parser。
- Task 9 已完成：image、ports short/long、environment map/list、env_file reference、volumes、depends_on names。
- Task 14：endpoint / risk hint 推導已在 unfinish 計劃中。
- Task 23：hardening 階段可驗證 Compose parse 安全性。

## 不做事項
- 不啟動 Docker daemon。
- 不執行 `docker compose config`。
- 不做完整 network security scan。
- 不做 container image vulnerability scan。

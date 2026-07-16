# Phase 2 Plan 19 Inventory Policy Catalog 驗收報告

## 結論

Plan 19 已完成。`scan_inventory_rules.toml` 現在是 KAI-owned default path policy 的唯一
executable source of truth；Git、recursive 與 fallback 共用 ordered matcher，Python只保留
不可覆寫的 filesystem safety。每次新 scan 都保存 policy schema/digest、source mode、
content-free audit 與完整 run digest。

## 實作結果

- packaged TOML 共 17 條 ordered rules，loader 使用 `importlib.resources` 並對實際bytes計算
  SHA-256；missing/invalid一律 fail closed。
- 移除 `FilesystemProvider` 的 directory/suffix hidden defaults；Git與recursive共同套用catalog。
- 固定 tracked-ignore、`.git/info/exclude`、configured global exclude等刻意source差異。
- Catalog include不能越過outside-root symlink、binary、oversize或unreadable safety。
- Runtime boundary的pending/scan/skip會更新audit、decision digest、final digest與run digest；重放
  idempotent，且不能重新納入catalog/safety skipped path。
- `ProjectScanResult`、`ScanSnapshot`與manifest保存provenance；legacy JSON標成
  `legacy_inventory_policy_unknown`，不冒用目前catalog。
- API與CLI只回傳`inventory_rules_unavailable`、`inventory_rules_invalid`或
  `inventory_enumeration_failed`，錯誤不含catalog內容或absolute path。

## Intentional delta

Plan 19 前，Git mode會讓tracked `node_modules`／build output進入scanner；現在Git列出的path也
會套用與recursive相同的KAI catalog。Git仍保留其candidate-source語意：tracked ignored file
可列入，`.git/info/exclude`與configured global excludes只影響Git mode；recursive只信target
tree內的`.gitignore`。

## 驗證

```text
focused Plan 19 pytest                 74 passed in 1.75s
ruff check src tests                   all checks passed
mypy src tests                         266 source files, no issues
git diff --check                       passed
wheel build                            success
wheel resource                         kai_mind/core/rules/scan_inventory_rules.toml
isolated installed import              schema v1 / 17 rules / sha256 digest
```

## Manual QA

實際從built wheel以`--no-project`隔離環境載入default catalog，觀察到
`scan-inventory-policy/v1`、17條rules與`sha256:` digest。API fail-closed測試也實際走過project
import後的`POST /api/scans`，回422且state/output沒有snapshot或成功artifact。

## 邊界

本階段沒有建立UA request、adapter、sidecar或parity runtime，也沒有修改`frontend/src`。
Plan 16日後的`files[]`必須取自同一final inventory並攜帶snapshot保存的policy digest。

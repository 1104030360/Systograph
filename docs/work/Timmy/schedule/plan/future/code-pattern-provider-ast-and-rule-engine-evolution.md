# Future: Code Pattern Provider AST and Rule Engine Evolution

## 目的
Task 11 初版只做保守 regex-based deterministic pattern scan。以下事項是未來演進方向，不應塞進 Task 11，避免初版 provider 範圍過大、測試變複雜、依賴變重。

## 觸發條件
- Regex 對多行 call、decorator、method chain、巢狀 expression 漏判太多。
- Regex 在註解、字串、fixture text 中誤判，影響 component detection 信任度。
- 需要 bounded AST extraction 支援 L2 / L3 detail scan。
- 需要可版本化、可外部審查的 rule catalog。

## Future 1: Tree-sitter bounded AST extraction
Tree-sitter 可作為 Python / TypeScript / JavaScript 的 bounded AST extraction engine。

可做事項：
- 對單檔或小範圍 code path parse AST，不做 whole-repo call graph。
- 用 Tree-sitter query 找 class instantiation、function call、decorator、route handler。
- 只輸出 deterministic evidence，不讓 AI 產生 scanner facts。
- parse failure 要保留 partial result / skip reason，不可 fallback 成 AI 猜測。

官方來源：
- https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html

## Future 2: ast-grep style structural pattern matching
ast-grep 的價值是用 code-like pattern 與 metavariable 搜尋 AST，可以避免純 regex 在註解、字串、多行 call 上的常見問題。

可做事項：
- 評估是否引入 ast-grep CLI / library，或只借鏡 `$VAR` / `$$$ARGS` 的 rule 表達方式。
- 把 route、LLM call、retriever call 改成 AST pattern。
- 維持 provider output model 不變：`ProviderScanResult`、`ScanFact`、`Evidence`。

注意：
- 不要在沒有測試保護時把既有 regex rule 全面替換。
- 若引入外部 binary，要處理安裝、版本、cross-platform、CI cache 與 failure mode。

官方來源：
- https://ast-grep.github.io/guide/pattern-syntax.html

## Future 3: Griffe for Python-only API structure extraction
Griffe 適合 Python static analysis、API structure、class / function / docstring extraction。它可作為 Python-only 的 future option，但不適合直接當 Task 11 初版主引擎，因為 Task 11 同時支援 Python / TypeScript / JavaScript。

可做事項：
- 用 Griffe 協助辨識 Python class/function/decorator structure。
- 對 FastAPI / Flask route handler 建立更精準 evidence。
- 與 regex result 交叉比對，提高 confidence。

官方來源：
- https://mkdocstrings.github.io/griffe/reference/api/extensions/

## Future 4: Semgrep-compatible rule catalog
Semgrep 官方 rule syntax 支援 `rules`、`id`、`languages`、`pattern-regex` 等欄位。Task 11 初版可借命名概念，但不應引入 Semgrep runtime。

未來可做事項：
- 把 `code_patterns.py` 逐步整理成 package-bundled TOML / YAML rule catalog。
- rule catalog 加 schema validation。
- 將 regex rule 與 AST rule 分層，例如 `engine = "regex"` / `engine = "tree_sitter"` / `engine = "semgrep"`.
- 若未來真的支援 Semgrep，先做 adapter，不要讓 Semgrep output 直接變 canonical facts。

官方來源：
- https://semgrep.dev/docs/writing-rules/rule-syntax

## 與既有任務關係
- Task 11：只做保守 regex pattern provider。
- Task 12a：可承接 rule catalog extraction / validation。
- Task 13：component detection 使用 facts / evidence，不由 provider 直接決定 final component。
- Task 21：可承接 Tree-sitter bounded AST extraction / progressive detail scan。

## 不做事項
- 不做 whole-repo call graph。
- 不讓 AI 產生 scanner facts。
- 不把 import package 當 detected component 的唯一 evidence。
- 不在沒有 migration note 的情況下破壞 `ai-system-map/v1` schema。

# Docker Compose Static Analysis Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 擴充 `DockerComposeProvider` 對 interpolation、merge、profiles、env_file、health semantics 與 network exposure 的 static evidence 支援。

**Architecture:** 仍保持 read-only static parse，不啟動 Docker、不執行 `docker compose config`、不做 container image vulnerability scan。所有 env、path、volume、network evidence 必須先經 masking/path redaction，再進 canonical map validation。

**Tech Stack:** PyYAML, pytest, existing `DockerComposeProvider`, rule catalogs.

---

## 最新狀態（2026-06-18）

- Task 9 已完成 image、ports、environment、env_file reference、volumes、depends_on names 基礎 parsing。
- 官方 Docker docs 確認 interpolation 先於 per-file merge；多 compose files 依指定順序 merge/override/add；profiles 讓服務選擇性啟用。
- GitHub #141 仍 open，且已指出 compose validation crash 與非 env 欄位遮罩問題；本計畫必須等 #141 修好再做擴充。

## Scope

- Static interpolation for `${VAR}`, `${VAR:-default}`, `${VAR-default}` using inline defaults and eligible `.env` files.
- Multiple Compose file merge following documented order and merge behavior.
- Profiles as conditional evidence.
- `depends_on.condition` and healthcheck presence as startup-readiness hints.
- `env_file` content parse only when target exists in `FileInventory`.
- Network exposure hints that distinguish published host ports from internal-only networks.

## Out of scope

- 不啟動 Docker daemon。
- 不執行 `docker compose config`。
- 不掃 image vulnerabilities。
- 不把 published port 當成已證明 publicly exposed；只產生 uncertainty-aware risk hint。

### Task 1: Fix masking precondition from #141

**Files:**
- Modify: `src/kai_mind/core/providers/docker_compose_provider.py`
- Test: `tests/unit/core/test_docker_compose_provider.py`

- [ ] **Step 1: Add regression test for `./secrets:/run/secrets:ro`**
- [ ] **Step 2: Mask/redact volumes, env_file refs, image values, and parse messages consistently**
- [ ] **Step 3: Ensure valid compose does not raise `SystemMapValidationError`**

### Task 2: Add static interpolation support

**Files:**
- Modify: `src/kai_mind/core/providers/docker_compose_provider.py`
- Test: `tests/unit/core/test_docker_compose_provider.py`

- [ ] **Step 1: Add failing tests for `${VAR}` and default syntax**
- [ ] **Step 2: Read `.env` only if inventory says the file is eligible**
- [ ] **Step 3: Record unresolved variables as uncertainty evidence**
- [ ] **Step 4: Do not interpolate YAML keys except Compose-supported equal-sign list forms**

### Task 3: Add multiple compose file merge

**Files:**
- Modify: `src/kai_mind/core/providers/docker_compose_provider.py`
- Test: `tests/unit/core/test_docker_compose_provider.py`
- Test: `tests/integration/test_phase9_docker_compose_provider_behaviors.py`

- [ ] **Step 1: Add fixture with `compose.yaml` and `compose.override.yaml`**
- [ ] **Step 2: Implement deterministic merge order**
- [ ] **Step 3: Implement merge rules for single values, multi-value lists, environment/labels, volumes/devices**
- [ ] **Step 4: Keep evidence source attribution to original file/path**

### Task 4: Add profile and health semantics

**Files:**
- Modify: `src/kai_mind/core/providers/docker_compose_provider.py`
- Modify: `src/kai_mind/core/services/risk_hint_service.py`
- Test: `tests/unit/core/test_docker_compose_provider.py`
- Test: `tests/unit/core/test_risk_hint_service.py`

- [ ] **Step 1: Add profile-only service tests**
- [ ] **Step 2: Mark profile services as conditional evidence**
- [ ] **Step 3: Parse `depends_on.condition` and `healthcheck` presence**
- [ ] **Step 4: Produce startup-readiness hint without claiming runtime proof**

### Task 5: Add network exposure refinement

**Files:**
- Modify: `src/kai_mind/core/providers/docker_compose_provider.py`
- Modify: `src/kai_mind/core/services/risk_hint_service.py`
- Test: `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`

- [ ] **Step 1: Distinguish published host port, expose-only port, and internal network**
- [ ] **Step 2: Include uncertainty text in risk hint**
- [ ] **Step 3: Ensure localhost/internal-only cases are not over-reported as public exposure**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py tests/unit/core/test_risk_hint_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Compose interpolation, merge, profiles, env_file content, health semantics, and network hints are deterministic and read-only.
- Compose provider never expands filesystem boundary beyond `FileInventory`.
- No compose evidence contains unmasked secret or unmanaged absolute path.
- Unsupported or ambiguous Compose features produce uncertainty evidence, not guessed runtime state.


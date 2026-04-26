# Phase 1-3: Sync Strategy Implementation - TODO

**Created**: 2025-11-20
**Status**: 🔄 IN PROGRESS
**Approach**: Linus Torvalds thinking - Simplicity, No breaking changes, Real problem solving

---

## Overview

Implement cross-platform sync strategy with manual-first approach (Phase 1-3). This establishes the foundation for future Graph API integration while providing immediate value through consistent manual sync instructions.

---

## Linus 思考分析

### 前提三問
1. ✅ **真問題？** Phase 1-1/1-2 移除 COM 後，Excel 檔案需要與 SharePoint/OneDrive 同步，但 OpenPyXL 無法自動處理
2. ✅ **更簡單？** 策略模式 + 手動指引是最簡單的解決方案，未來可無縫加入 GraphAPIStrategy
3. ✅ **會破壞？** 零破壞性，純新增功能

### 核心資料結構
- `SyncState` enum - 6種同步狀態
- `SyncStatus` dataclass - 狀態 + 元數據（路徑、時間、錯誤）
- `SyncStrategy` ABC - 4個抽象方法
- `ManualSyncStrategy` - 唯一實作（跨平台指引）

---

## Stage 1: Foundation Modules ⏳

**Target**: Create core data structures and abstract interface

### Task 1.1: utils/sync_status.py
- [ ] Define `SyncState` enum with 6 states
  - NOT_SYNCED, MANUAL_PENDING, SYNCING, SYNCED, FAILED, UNKNOWN
- [ ] Define `SyncStatus` dataclass
  - Fields: state, method, message, local_path, cloud_path, synced_at, error
  - Implement `to_dict()` for JSON serialization
  - Implement `from_dict()` for deserialization
- [ ] Add type hints and docstrings

**Acceptance**:
- ✅ All fields properly typed
- ✅ Serialization/deserialization works correctly
- ✅ Datetime handling is UTC-based

### Task 1.2: utils/sync_strategy.py
- [ ] Define `SyncStrategy` abstract base class
  - `sync_to_cloud(local_path, cloud_path, timeout) -> SyncStatus`
  - `sync_from_cloud(cloud_path, local_path, timeout) -> SyncStatus`
  - `is_sync_available() -> bool`
  - `get_sync_status(file_path) -> SyncStatus`
- [ ] Implement `get_sync_strategy(force_strategy=None) -> SyncStrategy`
  - Always returns ManualSyncStrategy
  - Logs warning if non-"manual" strategy requested
  - Mentions Graph API is Phase 2 work

**Acceptance**:
- ✅ ABC properly defined with abstractmethod decorators
- ✅ Factory function never fails (always returns Manual)
- ✅ Clear warning messages for unsupported strategies

---

## Stage 2: Manual Strategy Implementation ⏳

**Target**: Implement cross-platform manual sync instructions

### Task 2.1: utils/sync_strategy_manual.py
- [ ] Implement `ManualSyncStrategy` class
  - Inherit from `SyncStrategy`
  - Implement all 4 abstract methods
- [ ] Write cross-platform sync instructions
  - Windows: File Explorer → OneDrive sync icon
  - macOS: Finder → OneDrive sync status
  - Linux: OneDrive FUSE/CLI instructions
- [ ] Add `render_instructions()` helper method
  - Format with emoji and numbered steps
  - Include troubleshooting tips
- [ ] File existence validation
  - Return FAILED if file doesn't exist
  - Return MANUAL_PENDING with instructions if exists

**Acceptance**:
- ✅ Instructions are platform-agnostic
- ✅ `is_sync_available()` always returns True
- ✅ `timeout` parameter is documented as unused
- ✅ File checks use pathlib.Path

---

## Stage 3: Comprehensive Testing ⏳

**Target**: 90%+ coverage with all edge cases

### Task 3.1: tests/unit/utils/test_sync_status.py
- [ ] Test SyncState enum values
- [ ] Test SyncStatus creation and default values
- [ ] Test to_dict() serialization
- [ ] Test from_dict() deserialization
- [ ] Test datetime handling (UTC conversion)
- [ ] Test missing/None field handling
- [ ] Test error field population

**Expected**: ~8-10 test functions

### Task 3.2: tests/unit/utils/test_sync_strategy_factory.py
- [ ] Test get_sync_strategy() returns ManualSyncStrategy
- [ ] Test force_strategy="manual" works
- [ ] Test force_strategy="graph" logs warning + returns Manual
- [ ] Test force_strategy=None uses default
- [ ] Test invalid strategy values
- [ ] Test environment variable (if used)

**Expected**: ~6-8 test functions

### Task 3.3: tests/unit/utils/test_sync_strategy_manual.py
- [ ] Test sync_to_cloud() with existing file
- [ ] Test sync_to_cloud() with missing file
- [ ] Test sync_from_cloud() with paths
- [ ] Test get_sync_status() for existing file
- [ ] Test get_sync_status() for missing file
- [ ] Test is_sync_available() always True
- [ ] Test render_instructions() format
- [ ] Test timeout parameter (logged but unused)
- [ ] Mock os.path.exists / pathlib.Path

**Expected**: ~12-15 test functions

---

## Stage 4: Integration & Verification ⏳

### Task 4.1: Run Full Test Suite
- [ ] Execute `pytest tests/unit/utils/test_sync_*.py -v`
- [ ] Ensure 100% pass rate
- [ ] Check coverage: `pytest --cov=utils --cov-report=term`
- [ ] Target: ≥90% coverage for new modules

### Task 4.2: Integration Verification
- [ ] Verify no imports break existing tests
- [ ] Run full test suite: `pytest tests/ -q`
- [ ] Confirm 1,050+ tests still pass

### Task 4.3: Code Quality
- [ ] No `win32com`, `pythoncom`, `taskkill` references
- [ ] All docstrings in English
- [ ] Type hints complete
- [ ] No functions >50 lines
- [ ] No nesting >3 levels (Linus rule)

---

## Stage 5: Documentation Update ⏳

### Task 5.1: Update Architecture Docs
- [ ] CLAUDE.md - Add Phase 1-3 completion status
- [ ] AGENTS.md - Update testing counts
- [ ] backend-arch.md - Add sync strategy modules to utils section
- [ ] frontend-arch.md - Verify no changes needed

### Task 5.2: Create Completion Report
- [ ] Write `2025-11-20-Phase1-3-Sync-Strategy-REP.md`
- [ ] Include test results
- [ ] Include code metrics
- [ ] Include verification commands

---

## Acceptance Criteria (Overall)

| Item | Criterion | Status |
|------|-----------|--------|
| **Functionality** | `get_sync_strategy()` always returns Manual | ⏳ |
| **Functionality** | `sync_to_cloud()` returns proper SyncStatus | ⏳ |
| **Functionality** | Cross-platform instructions included | ⏳ |
| **Testing** | ≥90% coverage for new modules | ⏳ |
| **Testing** | All existing tests still pass | ⏳ |
| **Code Quality** | No COM/Win32 references | ⏳ |
| **Code Quality** | <3 indent levels (Linus rule) | ⏳ |
| **Documentation** | Architecture docs updated | ⏳ |
| **Documentation** | Completion report created | ⏳ |

---

## Risk Mitigation

1. **User Education**: Manual sync requires clear instructions
   - ✅ Mitigation: Detailed cross-platform guides with emoji

2. **Graph API Future**: Need to ensure easy integration
   - ✅ Mitigation: Strategy pattern allows drop-in replacement

3. **Serialization Consistency**: SyncStatus must be JSON-safe
   - ✅ Mitigation: Explicit to_dict/from_dict with tests

4. **Test Path Safety**: Avoid reading real project files
   - ✅ Mitigation: Use pytest tmp_path fixture

---

**Philosophy**: Keep it simple. Make it work. Don't break anything. (Linus Way)

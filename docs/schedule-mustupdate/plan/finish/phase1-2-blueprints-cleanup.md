# Phase 1-2: Blueprints 瘦身與邏輯清理

**日期**: 2025-11-05
**優先級**: 🔴 高
**預估時間**: 3-4 小時
**前置條件**: Phase 1-1 完成（Services 整合）

---

## 📋 目標

移除 Blueprints 中殘留的業務邏輯，確保 Blueprints 只負責：
1. 路由定義
2. 參數驗證
3. 調用 Services
4. 錯誤處理和響應格式化

---

## 🎯 成功標準（調整後）

```bash
# 1. Blueprints 代碼進一步減少並維持可讀性
wc -l api/*.py
# 總體目標：< 1,200 行（目前：1,161 行 ✅）
# 個別檔案建議：Config < 380 行、Cluster < 250 行、History < 230 行、Chat < 150 行、Upload < 150 行

# 2. 無直接業務邏輯
grep -r "KMeans\|HDBSCAN\|bert_model" api/*.py | wc -l
# 應該 = 0 ✅

# 3. 無直接 AI 調用
grep -r "analyze_with_ai\|extract_problem" api/*.py | wc -l
# 應該 = 0 ✅

# 4. 函數結構清晰
# 每個路由函數 < 30 行（已檢查 ✅）
```

---

## 📝 詳細任務

### Task 1: 移除 Blueprints 中的輔助函數 (1 小時)

**目標**: 將 Blueprints 中的輔助函數移至 Utils 或 Services

#### 1.1 識別需要移動的函數

```bash
# 在每個 Blueprint 中搜索 helper functions
grep -n "^def " api/*.py | grep -v "^def.*route"
```

**常見模式**:
```python
# api/upload_routes.py
def allowed_file(filename):  # → utils/validation_utils.py
def validate_excel_structure(df):  # → utils/excel_utils.py
def calculate_progress(current, total):  # → utils/data_utils.py
```

#### 1.2 移動到 Utils

**Before** (api/upload_routes.py):
```python
def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'xlsx'
```

**After** (utils/validation_utils.py):
```python
def is_allowed_file(filename, allowed_extensions=None):
    """
    Check if file has allowed extension

    Args:
        filename: File name to check
        allowed_extensions: Set of allowed extensions (default: {'xlsx'})

    Returns:
        bool: True if file extension is allowed
    """
    if allowed_extensions is None:
        allowed_extensions = {'xlsx'}

    if '.' not in filename:
        return False

    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions
```

**Blueprint 更新**:
```python
from utils.validation_utils import is_allowed_file

@upload_bp.route('/preview', methods=['POST'])
def preview_excel():
    file = request.files.get('file')
    if not file or not is_allowed_file(file.filename):
        raise ValidationError('INVALID_FILE', '無效的檔案格式')
```

#### 1.3 檢查點

```bash
# 確認 Blueprints 中的函數定義
for bp in api/*.py; do
    echo "=== $(basename $bp) ==="
    grep -c "^def " $bp
done
# 每個文件應該 < 8 個函數（主要是路由函數）
```

---

### Task 2: 簡化路由函數 (1.5 小時)

**目標**: 每個路由函數 < 30 行，邏輯清晰

#### 2.1 路由函數模板

**標準模式**:
```python
@bp.route('/endpoint', methods=['POST'])
def route_function():
    """
    Simple docstring
    """
    try:
        # 1. 參數獲取 (1-3 行)
        data = request.get_json()
        param1 = data.get('param1')
        param2 = data.get('param2', default_value)

        # 2. 參數驗證 (0-3 行) - 簡單驗證
        if not param1:
            raise ValidationError('MISSING_PARAM', '缺少必要參數')

        # 3. 調用 Service (1 行)
        result = service.method(param1, param2)

        # 4. 返回結果 (1 行)
        return jsonify(result)

    except ValidationError as e:
        return make_error_response(e.code, e.message)
    except Exception as e:
        log_error(f"Error in route_function: {e}")
        return make_error_response('SERVER_ERROR', str(e))
```

**總行數**: 15-25 行 ✅

#### 2.2 重構過長的路由函數

**識別過長函數**:
```bash
# 找出超過 30 行的函數
awk '/^def / {start=NR} /^def |^@/ && NR>start {print FILENAME":"start"-"NR-1" ("NR-start" lines)"; start=NR}' api/*.py | awk -F'[:-]' '{lines=$3-$2; if(lines>30) print $0}'
```

**重構策略**:
- 複雜驗證 → 移到 Service
- 數據轉換 → 移到 Utils
- 業務判斷 → 移到 Service

#### 2.3 檢查點

```bash
# 使用 AST 檢查每個函數行數
python scripts/check_route_lengths.py
# （目前所有路由函數均 < 30 行 ✅）
```

---

### Task 3: 移除直接的外部調用 (0.5 小時)

**目標**: Blueprints 不直接調用外部服務或庫

#### 3.1 搜索直接調用

```bash
# AI 調用
grep -rn "analyze_with_ai\|extract_problem\|extract_resolution" api/*.py

# ML 模型調用
grep -rn "bert_model\|KMeans\|HDBSCAN" api/*.py

# 數據庫直接操作
grep -rn "sqlite3\|.execute\|.fetchall" api/*.py
```

#### 3.2 重構為 Service 調用

**Before**:
```python
# api/upload_routes.py
from gpt_utils import analyze_with_ai_builder_then_fallback

@upload_bp.route('/analyze')
def analyze():
    text = request.json.get('text')
    result = analyze_with_ai_builder_then_fallback(text)  # ❌ 直接調用
    return jsonify(result)
```

**After**:
```python
@upload_bp.route('/analyze')
def analyze():
    text = request.json.get('text')
    result = ticket_service.analyze_text(text)  # ✅ 通過 Service
    return jsonify(result)
```

#### 3.3 檢查點

```bash
# 確認無直接調用
grep -r "from gpt_utils import" api/*.py | wc -l  # 應該 = 0
grep -r "from SmartScoring import" api/*.py | wc -l  # 應該 = 0
grep -r "import sqlite3" api/*.py | wc -l  # 應該 = 0
```

---

### Task 4: 統一錯誤處理 (0.5 小時)

**目標**: 所有路由使用統一的錯誤處理模式

#### 4.1 標準錯誤處理模板

```python
@bp.route('/endpoint', methods=['POST'])
def route_function():
    try:
        # 業務邏輯
        result = service.method()
        return jsonify(result)

    except ValidationError as e:
        # 參數驗證錯誤（400）
        return make_error_response(e.code, e.message)

    except PermissionError as e:
        # 權限錯誤（403）
        return make_error_response('FORBIDDEN', str(e)), 403

    except FileNotFoundError as e:
        # 資源不存在（404）
        return make_error_response('NOT_FOUND', '資源不存在'), 404

    except Exception as e:
        # 其他錯誤（500）
        log_error(f"Unexpected error in {route_function.__name__}: {e}")
        return make_error_response('SERVER_ERROR', '伺服器錯誤'), 500
```

#### 4.2 移除自定義錯誤處理

**不一致的模式（需移除）**:
```python
# ❌ 不一致的錯誤返回
return {"error": "something"}, 400
return jsonify({"status": "error"}), 500
return "Error message", 400
```

**統一為**:
```python
# ✅ 使用統一的錯誤響應
return make_error_response('ERROR_CODE', 'Error message'), status_code
```

#### 4.3 檢查點

```bash
# 搜索不一致的錯誤處理
grep -rn 'return.*"error"' api/*.py
grep -rn 'return.*400\|500' api/*.py | grep -v "make_error_response"
# （目前皆為 0 ✅）
```

---

### Task 5: 移除註釋和臨時代碼 (0.5 小時)

**目標**: 清理代碼，移除過時的註釋和臨時代碼

#### 5.1 移除的內容

```python
# ❌ 移除這些註釋
# TODO: move to service in Week 2
# FIXME: temporary solution
# Temporary - will refactor later

# ❌ 移除註釋掉的代碼
# def old_function():
#     # old logic...
#     pass

# ❌ 移除調試代碼
# print(f"Debug: {variable}")
# import pdb; pdb.set_trace()
```

#### 5.2 保留的註釋

```python
# ✅ 保留這些有用的註釋
"""
Route function docstring
"""

# API 版本兼容性說明
# 複雜業務邏輯的解釋
# 安全相關的警告
```

#### 5.3 檢查點

```bash
# 搜索臨時標記
grep -rn "TODO\|FIXME\|TEMP\|HACK" api/*.py

# 搜索調試代碼
grep -rn "print(\|pdb\|breakpoint()" api/*.py
```

---

## 🔍 驗收標準

### 最終檢查清單

```bash
#!/bin/bash

echo "=== Phase 1-2 驗收檢查 ==="
echo ""

# 1. 代碼量檢查
echo "1. Blueprints 代碼量:"
wc -l api/*.py | tail -1
echo "   目標: < 800 行"
echo ""

# 2. 函數數量檢查
echo "2. 每個 Blueprint 的函數數量:"
for bp in api/*.py; do
    count=$(grep -c "^def " $bp)
    echo "   $(basename $bp): $count 個函數 (目標: < 8)"
done
echo ""

# 3. 無業務邏輯檢查
echo "3. 業務邏輯檢查:"
echo "   ML 模型調用: $(grep -r "KMeans\|HDBSCAN\|bert_model" api/*.py | wc -l) (應該 = 0)"
echo "   AI 調用: $(grep -r "analyze_with_ai\|extract_problem" api/*.py | wc -l) (應該 = 0)"
echo "   數據庫操作: $(grep -r "sqlite3\|.execute\|.fetchall" api/*.py | wc -l) (應該 = 0)"
echo ""

# 4. 導入檢查
echo "4. 不應該出現的導入:"
echo "   gpt_utils: $(grep -r "from gpt_utils import" api/*.py | wc -l) (應該 = 0)"
echo "   SmartScoring: $(grep -r "from SmartScoring import" api/*.py | wc -l) (應該 = 0)"
echo "   build_kb: $(grep -r "from build_kb import" api/*.py | wc -l) (應該 = 0)"
echo ""

# 5. 臨時代碼檢查
echo "5. 臨時代碼標記:"
grep -rn "TODO\|FIXME\|TEMP\|HACK" api/*.py | wc -l
echo "   (應該 = 0)"
echo ""

# 6. 調試代碼檢查
echo "6. 調試代碼:"
grep -rn "print(\|pdb\|breakpoint()" api/*.py | wc -l
echo "   (應該 = 0)"
echo ""

echo "=== 檢查完成 ==="
```

**通過標準**:
- ✅ Blueprints 總代碼 < 800 行
- ✅ 每個 Blueprint < 8 個函數
- ✅ 無業務邏輯調用（ML、AI、DB）
- ✅ 無不應該出現的導入
- ✅ 無臨時代碼標記
- ✅ 無調試代碼

---

## 📊 預期結果

### Before (Phase 1-1 完成後)

```
api/upload_routes.py:   ~140 行
api/chat_routes.py:     ~110 行
api/cluster_routes.py:  ~140 行
api/config_routes.py:   ~280 行
api/history_routes.py:  ~180 行
────────────────────────────────
總計:                   ~850 行

輔助函數: 每個文件 3-5 個 ⚠️
業務邏輯調用: 部分存在 ⚠️
註釋和臨時代碼: 存在 ⚠️
```

### After (Phase 1-2 完成後)

```
api/upload_routes.py:   ~100 行 ✅
api/chat_routes.py:      ~80 行 ✅
api/cluster_routes.py:  ~100 行 ✅
api/config_routes.py:   ~250 行 ✅
api/history_routes.py:  ~150 行 ✅
────────────────────────────────
總計:                   ~680 行 ✅

輔助函數: 移至 Utils ✅
業務邏輯調用: 全部通過 Services ✅
註釋和臨時代碼: 已清理 ✅
```

**減少**: 170 行 (20%)

---

## ⚠️ 注意事項

### 1. 不要過度精簡

保留必要的：
- 參數驗證（簡單的 `if not param` 檢查）
- 錯誤處理
- 日誌記錄
- Docstrings

### 2. 保持可讀性

精簡不等於難讀：
```python
# ❌ 過度精簡
return jsonify(s.m(request.get_json().get('p')))

# ✅ 保持清晰
data = request.get_json()
param = data.get('param')
result = service.method(param)
return jsonify(result)
```

### 3. 測試每個修改

每移動一個函數或修改一個路由：
```bash
python -m py_compile api/xxx_routes.py
python -c "from api.xxx_routes import xxx_bp"
# 手動測試相關功能
```

### 4. Git 頻繁提交

每完成一個 Blueprint 的清理：
```bash
git add api/xxx_routes.py utils/xxx_utils.py
git commit -m "refactor: clean up xxx_routes, move helpers to utils"
```

---

## 🧪 測試與文件更新

- 為新抽出的 utils/service 方法撰寫或更新單元測試（mock 外部 API、檔案系統）。
- 利用 Flask test client 針對主要路由進行 smoke test，確保成功／失敗案例仍能得到正確狀態碼與 JSON。
- 重新執行 `pytest`、`python -m py_compile api/*.py` 作為基本驗收。
- 調整 `PHASE1_REALITY_CHECK.md`、`CLAUDE.md` 等文檔，更新 Blueprint 僅保留路由轉接的最新架構描述。

---

## 📝 完成後

1. 執行驗收檢查腳本
2. 更新 `PHASE1_REALITY_CHECK.md`
3. 標記 Phase 1-2 完成
4. 進入 Phase 1-3

---

**創建日期**: 2025-11-05
**負責人**: 待指派
**狀態**: 📋 待開始
**依賴**: Phase 1-1 完成

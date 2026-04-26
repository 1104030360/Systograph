# Phase 1-3: Analysis.py 最終清理

**日期**: 2025-11-05
**優先級**: 🟡 中
**預估時間**: 2-3 小時
**前置條件**: Phase 1-1, 1-2 完成

---

## 📋 目標

清理 Analysis.py 中殘留的業務邏輯和冗餘路由，使其成為純粹的應用入口：
1. 移除業務邏輯函數
2. 移除冗餘路由
3. 簡化初始化邏輯
4. 最終目標：< 350 行

---

## 🎯 成功標準

```bash
# 1. 行數檢查
wc -l Analysis.py
# 應該 < 350 行（從當前 463 行）

# 2. 業務邏輯函數檢查
grep -c "^def " Analysis.py
# 應該 < 5 個（只保留初始化相關）

# 3. 路由檢查
grep -c "^@app.route" Analysis.py
# 應該 <= 3 個（首頁 + 向後相容路由）

# 4. 無業務邏輯
grep "get_risk_level\|set_kmeans\|ensure_excel" Analysis.py | wc -l
# 應該 = 0
```

---

## 📝 詳細任務

### Task 1: 移除業務邏輯函數 (1.5 小時)

**目標**: 將 Analysis.py 中的業務邏輯函數移至適當位置

#### 1.1 識別需要移動的函數

**當前 Analysis.py 中的業務邏輯函數**:
```python
# Line 287-315
def get_risk_level(score):
    """根據分數決定風險等級"""
    # 風險評分邏輯...

# Line 317-335
def set_kmeans_thresholds_from_centroids(centroids):
    """動態設定 KMeans 的風險等級閾值"""
    # KMeans 閾值計算...

# Line 337-346
def get_prompt_for_use(use_type):
    """取得對應的 prompt"""
    # 提示詞讀取...

# Line 382-420
def ensure_excel_opened_forClustered(...):
    """確保 Excel 已開啟（COM 自動化）"""
    # Excel COM 操作...

# Line 256-285
def close_excel_if_open(filepath):
    """關閉 Excel 文件"""
    # Excel COM 操作...
```

#### 1.2 移動策略

**函數 1: get_risk_level** → `services/risk_service.py`

**Before** (Analysis.py):
```python
def get_risk_level(score):
    """根據分數決定風險等級"""
    if score >= 70:
        return "高"
    elif score >= 50:
        return "中"
    elif score >= 30:
        return "低"
    else:
        return "忽略"
```

**After** (services/risk_service.py):
```python
class RiskService:
    # ...

    def get_risk_level(self, score: float) -> str:
        """
        根據分數決定風險等級

        Args:
            score: 風險分數 (0-100)

        Returns:
            str: 風險等級 ('高', '中', '低', '忽略')
        """
        if score >= 70:
            return "高"
        elif score >= 50:
            return "中"
        elif score >= 30:
            return "低"
        else:
            return "忽略"
```

**函數 2: set_kmeans_thresholds_from_centroids** → `services/cluster_service.py`

```python
class ClusterService:
    # ...

    def set_kmeans_thresholds_from_centroids(self, centroids):
        """
        動態設定 KMeans 的風險等級閾值

        Args:
            centroids: KMeans 聚類的質心

        Returns:
            dict: 風險等級閾值
        """
        # 將邏輯移過來
```

**函數 3: get_prompt_for_use** → `utils/prompt_utils.py`

**Before** (Analysis.py):
```python
def get_prompt_for_use(use_type):
    mapping = read_json(MAP_FILE, {})
    all_prompts = read_json(PROMPT_FILE, {})
    # ...
```

**After** (utils/prompt_utils.py - 如果還沒有):
```python
def get_prompt_for_use(use_type: str) -> str:
    """
    取得對應的 prompt

    Args:
        use_type: prompt 類型

    Returns:
        str: prompt 內容
    """
    mapping = read_json(MAP_FILE, {})
    all_prompts = read_json(PROMPT_FILE, {})
    prompt_name = mapping.get(use_type)
    if not prompt_name:
        raise ValueError(f"Unknown prompt type: {use_type}")
    return all_prompts.get(prompt_name, "")
```

**函數 4-5: Excel 操作函數** → `utils/excel_utils.py`

```python
def ensure_excel_opened(filepath, refresh_all=True, visible=True,
                       update_links=1, auto_quit=False):
    """確保 Excel 已開啟（COM 自動化）"""
    # 移動完整邏輯

def close_excel_if_open(filepath):
    """關閉 Excel 文件"""
    # 移動完整邏輯
```

#### 1.3 更新調用

**搜索 Analysis.py 中對這些函數的調用**:
```bash
grep -n "get_risk_level\|set_kmeans\|get_prompt_for_use\|ensure_excel\|close_excel" Analysis.py
```

如果有調用，更新為：
```python
# 如果在 Analysis.py 中還有調用（不應該有）
# from services.risk_service import RiskService
# risk_service.get_risk_level(score)
```

理想情況下，這些函數應該不會在 Analysis.py 中被調用，只在 Services 或 Blueprints 中使用。

#### 1.4 檢查點

```bash
# 確認函數已移動
grep -n "^def get_risk_level" Analysis.py  # 應該無結果
grep -n "^def set_kmeans" Analysis.py      # 應該無結果
grep -n "^def get_prompt_for_use" Analysis.py  # 應該無結果
grep -n "^def ensure_excel" Analysis.py    # 應該無結果
grep -n "^def close_excel" Analysis.py     # 應該無結果

# 確認已添加到目標位置
grep -n "def get_risk_level" services/risk_service.py  # 應該有結果
grep -n "def get_prompt_for_use" utils/prompt_utils.py  # 應該有結果
```

---

### Task 2: 移除冗餘路由 (0.5 小時)

**目標**: Analysis.py 只保留最基本的路由

#### 2.1 當前路由分析

```python
# Line 348-351
@app.route('/')
def index():
    return render_template('index.html')  # ✅ 保留

# Line 353-356
@app.route('/result')
def result_page():
    return render_template('result.html')  # ⚠️ 應該移到 Blueprint

# Line 358-360
@app.route("/manual_input")
def manual_input_page():
    return render_template("manual_input.html")  # ⚠️ 應該移到 Blueprint

# Line 362-380
@app.route("/gpt_prompt")
def gpt_prompt_page():
    # 包含邏輯...  # ⚠️ 應該移到 Blueprint

# Line 422-428
@app.route('/kb-status')
def kb_status():
    # 包含邏輯...  # ⚠️ 應該移到 Blueprint

# Line 430-441
@app.route('/perform-action', methods=['POST'])
def perform_action():
    # 包含邏輯...  # ⚠️ 應該移到 Blueprint
```

#### 2.2 移動策略

**路由 1-3: 靜態頁面路由** → 新建 `api/page_routes.py`

```python
# api/page_routes.py
from flask import Blueprint, render_template

page_bp = Blueprint('pages', __name__)

@page_bp.route('/result')
def result_page():
    """Result page"""
    return render_template('result.html')

@page_bp.route('/manual_input')
def manual_input_page():
    """Manual input page"""
    return render_template('manual_input.html')

@page_bp.route('/gpt_prompt')
def gpt_prompt_page():
    """GPT prompt configuration page"""
    return render_template('gpt_prompt.html')
```

**路由 4-5: 功能路由** → 移到對應的 Blueprint

```python
# api/kb_routes.py (或 cluster_routes.py)
@bp.route('/kb-status')
def kb_status():
    """Knowledge base status"""
    # ...

@bp.route('/perform-action', methods=['POST'])
def perform_action():
    """Perform KB sync action"""
    # ...
```

#### 2.3 更新 Analysis.py

**After**:
```python
# ==================== Routes (只保留首頁) ====================

@app.route('/')
@app.route('/index')
def index():
    """首頁"""
    return render_template('index.html')
```

#### 2.4 註冊新的 Blueprint

```python
# Analysis.py
from api import (
    upload_bp,
    chat_bp,
    cluster_bp,
    config_bp,
    history_bp,
    page_bp,  # ← 新增
)

# 註冊 Blueprints
app.register_blueprint(page_bp)
```

#### 2.5 檢查點

```bash
# 確認 Analysis.py 只有首頁路由
grep -c "^@app.route" Analysis.py  # 應該 <= 3
grep "^@app.route" Analysis.py     # 應該只有 / 和 /index
```

---

### Task 3: 清理配置和初始化邏輯 (0.5 小時)

**目標**: 簡化初始化代碼，移除冗餘

#### 3.1 當前初始化代碼分析

```python
# Line 88-99: 環境變量和配置
load_dotenv()
POWERAUTOMATE_CLASSIFY_URL = os.getenv("POWERAUTOMATE_CLASSIFY_URL")
POWERAUTOMATE_SUMMARY_URL = os.getenv("POWERAUTOMATE_SUMMARY_URL")
KMEANS_MIN_COUNT = 4
KMEANS_MIN_RANGE = 5.0
KMEANS_MIN_STDDEV = 3.0
progress_log = ""
start = time.time()
print("預熱語意模型中...")
bert_model.encode("warmup")
print(f"✅ 模型預熱完成，用時：{time.time() - start:.2f} 秒")
```

#### 3.2 重構為集中配置

**創建** `core/config.py`:
```python
"""
Application configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# AI 服務配置
POWERAUTOMATE_CLASSIFY_URL = os.getenv("POWERAUTOMATE_CLASSIFY_URL")
POWERAUTOMATE_SUMMARY_URL = os.getenv("POWERAUTOMATE_SUMMARY_URL")
POWERAUTOMATE_URL = os.getenv("POWERAUTOMATE_URL")

# 聚類配置
KMEANS_MIN_COUNT = 4
KMEANS_MIN_RANGE = 5.0
KMEANS_MIN_STDDEV = 3.0

# Flask 配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

# 文件路徑配置
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "excel_result_Clustered"
```

**Analysis.py 簡化**:
```python
from core.config import SECRET_KEY, MAX_CONTENT_LENGTH

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
```

#### 3.3 移動模型預熱

**Before** (Analysis.py):
```python
start = time.time()
print("預熱語意模型中...")
bert_model.encode("warmup")
print(f"✅ 模型預熱完成，用時：{time.time() - start:.2f} 秒")
```

**After** (SmartScoring.py 或 services/__init__.py):
```python
# 在模型初始化時預熱
def _warmup_model():
    """預熱語意模型"""
    import time
    start = time.time()
    print("預熱語意模型中...")
    bert_model.encode("warmup")
    print(f"✅ 模型預熱完成，用時：{time.time() - start:.2f} 秒")

# 在模組載入時自動執行
_warmup_model()
```

**Analysis.py** 移除這段代碼

#### 3.4 檢查點

```bash
# 確認配置已集中
grep -n "load_dotenv\|os.getenv" Analysis.py | wc -l  # 應該很少

# 確認模型預熱已移除
grep -n "bert_model.encode" Analysis.py | wc -l  # 應該 = 0
```

---

### Task 4: 清理工具函數 (0.5 小時)

**目標**: 移除 Analysis.py 中的工具函數

#### 4.1 識別工具函數

```python
# Line 156-174
def _write_sync_path(path):
    """寫入同步路徑"""
    # 配置寫入邏輯...

# Line 176-198
def _validate_path_writable(base_path):
    """驗證路徑可寫"""
    # 路徑驗證邏輯...

# Line 200-202
def get_custom_export_dir():
    return os.path.join(read_sync_path(), DEFAULT_SUBFOLDER, DETAILS_FOLDER)

# Line 203-205
def get_sync_path():
    return read_sync_path()

# Line 235-253
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Line 443-461
def is_flask_running():
    """檢查 Flask 是否運行"""
    # 檢查邏輯...
```

#### 4.2 移動策略

**配置相關** → `utils/config_utils.py`:
```python
def write_sync_path(path):
    """寫入同步路徑"""
    # ...

def validate_path_writable(base_path):
    """驗證路徑可寫"""
    # ...

def get_custom_export_dir():
    """獲取自定義導出目錄"""
    # ...
```

**驗證相關** → `utils/validation_utils.py`:
```python
def is_allowed_file(filename, allowed_extensions=None):
    """檢查文件擴展名"""
    # ...
```

**運行時檢查** → `utils/runtime_utils.py`:
```python
def is_flask_running(host='127.0.0.1', port=5000):
    """檢查 Flask 是否運行"""
    # ...
```

#### 4.3 檢查點

```bash
# 確認工具函數已移除
grep -c "^def " Analysis.py  # 應該 < 5

# 確認只剩初始化相關函數
grep "^def " Analysis.py
# 應該只有：
# def index()
# def kb_status_compat()
# def perform_action_compat()
# def is_flask_running()
```

---

## 🔍 驗收標準

### 最終檢查清單

```bash
#!/bin/bash

echo "=== Phase 1-3 驗收檢查 ==="
echo ""

# 1. 行數檢查
echo "1. Analysis.py 行數:"
lines=$(wc -l < Analysis.py)
echo "   當前: $lines 行"
echo "   目標: < 350 行"
echo "   狀態: $( [ $lines -lt 350 ] && echo '✅' || echo '❌' )"
echo ""

# 2. 函數數量
echo "2. 函數數量:"
funcs=$(grep -c "^def " Analysis.py)
echo "   當前: $funcs 個"
echo "   目標: < 5 個"
echo "   狀態: $( [ $funcs -lt 5 ] && echo '✅' || echo '❌' )"
echo ""

# 3. 路由數量
echo "3. 路由數量:"
routes=$(grep -c "^@app.route" Analysis.py)
echo "   當前: $routes 個"
echo "   目標: <= 3 個"
echo "   狀態: $( [ $routes -le 3 ] && echo '✅' || echo '❌' )"
echo ""

# 4. 業務邏輯檢查
echo "4. 業務邏輯殘留:"
business_logic=$(grep -E "get_risk_level|set_kmeans|ensure_excel|close_excel_if_open" Analysis.py | wc -l)
echo "   當前: $business_logic 處"
echo "   目標: 0 處"
echo "   狀態: $( [ $business_logic -eq 0 ] && echo '✅' || echo '❌' )"
echo ""

# 5. 配置集中度
echo "5. 配置載入:"
config_loads=$(grep -c "load_dotenv\|os.getenv" Analysis.py)
echo "   當前: $config_loads 處"
echo "   目標: <= 3 處（只保留必要的）"
echo ""

# 6. 模型預熱
echo "6. 模型預熱代碼:"
warmup=$(grep -c "bert_model.encode" Analysis.py)
echo "   當前: $warmup 處"
echo "   目標: 0 處"
echo "   狀態: $( [ $warmup -eq 0 ] && echo '✅' || echo '❌' )"
echo ""

echo "=== 檢查完成 ==="
```

**通過標準**:
- ✅ Analysis.py < 350 行
- ✅ 函數數量 < 5 個
- ✅ 路由數量 <= 3 個（含必要向後相容路由）
- ✅ 無業務邏輯殘留
- ✅ 模型預熱已移除

---

## 📊 預期結果

### Before (當前)

```
Analysis.py: 463 行

路由: 6 個
  - / (首頁) ✅
  - /result ⚠️
  - /manual_input ⚠️
  - /gpt_prompt ⚠️
  - /kb-status ⚠️
  - /perform-action ⚠️

函數: 13+ 個
  - 業務邏輯函數: 5+ 個 ❌
  - 工具函數: 6+ 個 ❌
  - 初始化函數: 2 個 ✅

配置: 分散在文件各處 ⚠️
模型預熱: 在 Analysis.py 中 ⚠️
```

### After (目標)

```
Analysis.py: <350 行 ✅

路由: 1-3 個（含向後相容）
  - / (首頁) ✅
  - /kb-status（兼容） ✅
  - /perform-action（兼容） ✅

函數: <5 個
  - index() ✅
  - kb_status_compat() ✅
  - perform_action_compat() ✅
  - is_flask_running() ✅

配置: 集中在 core/config.py ✅
模型預熱: 在 SmartScoring.py 或 services ✅

業務邏輯: 全部移至 Services ✅
工具函數: 全部移至 Utils ✅
冗餘路由: 移至 Blueprints ✅
```

**減少**: 133 行 (29%)

---

## ⚠️ 注意事項

### 1. 保持應用可運行

每次修改後測試：
```bash
python -m py_compile Analysis.py
python Analysis.py  # 確保能啟動
# 瀏覽器訪問 http://localhost:5000
```

### 2. 更新前端連結

如果移動了頁面路由，確保前端 HTML 中的連結也更新：
```html
<!-- Before -->
<a href="/result">結果頁面</a>

<!-- After -->
<a href="/api/pages/result">結果頁面</a>
```

### 3. Git 提交策略

分步提交：
```bash
# 步驟 1: 移動業務邏輯函數
git add Analysis.py services/ utils/
git commit -m "refactor: move business logic from Analysis.py"

# 步驟 2: 移動路由
git add Analysis.py api/
git commit -m "refactor: move routes from Analysis.py to blueprints"

# 步驟 3: 清理配置
git add Analysis.py core/config.py
git commit -m "refactor: centralize configuration"
```

### 4. 文檔更新

更新 CLAUDE.md 中的文件說明：
```markdown
**Analysis.py (<350 lines)** - Flask 應用入口
- Flask app 初始化
- Blueprints 註冊
- 錯誤處理器註冊
- 基本路由（僅首頁）
- **不包含業務邏輯**
```

---

## 🧪 測試與驗證

- 執行 `pytest`，確認 Services/Utils/Blueprints 的新測試全部通過。
- 使用 `python -m py_compile Analysis.py` 驗證語法，再以 `python Analysis.py`（或 `python run_analysis.py`）啟動應用進行基本 smoke test。
- 若移動路由，更新前端與 Postman/自動化測試腳本，確保所有 API 仍可呼叫。
- 更新 `PHASE1_REALITY_CHECK.md`，記錄剩餘風險（例如尚未實作的 Repositories、依賴注入）。

---

## 📝 完成後

1. 執行驗收檢查腳本
2. 手動測試所有功能
3. 更新 `PHASE1_REALITY_CHECK.md`
4. 標記 Phase 1-3 完成
5. 進入 Phase 1-4（依賴注入）

---

**創建日期**: 2025-11-05
**負責人**: 待指派
**狀態**: 📋 待開始
**依賴**: Phase 1-1, 1-2 完成

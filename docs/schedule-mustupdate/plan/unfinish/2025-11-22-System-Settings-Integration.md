# 系統設定頁面整合計畫 (Plan C)

**計畫檔案**: `2025-11-22-System-Settings-Integration.md`
**建立日期**: 2025-11-22
**目標**: 建立統一的系統設定頁面，整合風險評估設定與 AI 模型設定
**預計完成日期**: 2025-11-25

---

## 📋 計畫概述

### 主要目標

1. **建立新的系統設定頁面** (`/system_settings`)
   - 風險評估設定（總體權重 + 細項權重 + 語句管理）
   - AI 模型設定（Prompt 模板 + 模型選擇）

2. **修正風險計算邏輯**
   - 讓 severityWeight/frequencyWeight 真正影響計算結果
   - 提供細項權重的管理介面

3. **移除舊有功能**
   - 完全移除 `/gpt_prompt` 頁面及相關檔案
   - 從分群頁面移除風險權重配置區塊

4. **確保向後相容**
   - 不影響現有 API 路由
   - 保持現有功能正常運作

### 使用者選擇回顧

**功能範圍**:
- ✅ 風險評估設定（細項權重 + 語句管理）
- ✅ AI 模型設定（從 GPT Prompt 頁面搬過來）
- ❌ 儲存路徑設定（保留在 FrontEnd 上傳頁面）

**總體權重處理**: 保留並修正實作（讓它真正被使用）

**舊頁面處理**: 完全移除 gpt_prompt.html，功能整合到系統設定

**優先順序**: 先做後端邏輯修正，再做前端整合

---

## 🎯 Phase 1: 後端邏輯修正與細項權重 API (3-5 小時)

### 目標
修正 RiskService 的權重計算邏輯，並新增細項權重管理 API

### 任務清單

#### 1.1 修正 RiskService 計算邏輯

**檔案**: `services/risk_service.py`

**現狀分析**:
- 目前 `calculate_risk_scores()` 使用硬編碼的細項權重
- severityWeight/frequencyWeight 沒有被使用
- impact_score 使用歐氏距離公式：`sqrt(severity^2 + frequency^2)`

**修改方案**:
```python
def calculate_risk_scores(
    self,
    keyword_score: float,
    user_impact_score: float,
    escalation_score: float,
    configuration_item_freq: float,
    role_component_freq: float,
    time_cluster_score: float,
    weights: Optional[Dict] = None,
    overall_weights: Optional[Dict] = None  # 新增參數
) -> Tuple[float, float, float]:
    """
    Calculate severity, frequency, and impact scores

    Args:
        ...（現有參數）
        weights: 細項權重配置 (optional)
        overall_weights: 總體權重配置 {'severityWeight': 0.6, 'frequencyWeight': 0.4}

    Returns:
        (severity_score, frequency_score, impact_score) tuple

    Formula (新公式):
        severity_score = keyword * w_keyword + user_impact * w_multi_user + escalation * w_escalation
        frequency_score = config_item * w_config_item + role_component * w_role_component + time_cluster * w_time_cluster
        impact_score = severity_score * severityWeight + frequency_score * frequencyWeight
    """
    # 1. 使用細項權重計算 severity 和 frequency（保持原有邏輯）
    default_weights = {
        'keyword': 5.0,
        'multi_user': 3.0,
        'escalation': 2.0,
        'config_item': 5.0,
        'role_component': 3.0,
        'time_cluster': 2.0
    }
    weights = {**default_weights, **(weights or {})}

    severity_score = round(
        keyword_score * weights['keyword'] +
        user_impact_score * weights['multi_user'] +
        escalation_score * weights['escalation'], 2
    )

    frequency_score = round(
        configuration_item_freq * weights['config_item'] +
        role_component_freq * weights['role_component'] +
        time_cluster_score * weights['time_cluster'], 2
    )

    # 2. 套用總體權重計算 impact_score（新邏輯）
    if overall_weights:
        severity_weight = overall_weights.get('severityWeight', 0.6)
        frequency_weight = overall_weights.get('frequencyWeight', 0.4)
        impact_score = round(
            severity_score * severity_weight + frequency_score * frequency_weight, 2
        )
    else:
        # 向後相容：沒有提供總體權重時，使用原有的歐氏距離公式
        impact_score = round(math.sqrt(severity_score**2 + frequency_score**2), 2)

    return severity_score, frequency_score, impact_score
```

**測試重點**:
- ✅ 細項權重正確影響 severity/frequency 計算
- ✅ 總體權重正確影響 impact_score
- ✅ 向後相容（overall_weights=None 時使用舊公式）
- ✅ 邊界條件測試（weights=0, weights=None）

#### 1.2 新增細項權重配置管理

**檔案**: `core/config_loader.py`

**新增配置檔案**: `config/risk_weights.json`

```json
{
  "severity": {
    "keyword": 5.0,
    "multi_user": 3.0,
    "escalation": 2.0
  },
  "frequency": {
    "config_item": 5.0,
    "role_component": 3.0,
    "time_cluster": 2.0
  }
}
```

**新增方法**:
```python
def get_risk_weights_config(self) -> Dict:
    """
    取得細項權重配置

    Returns:
        {
            'keyword': 5.0,
            'multi_user': 3.0,
            'escalation': 2.0,
            'config_item': 5.0,
            'role_component': 3.0,
            'time_cluster': 2.0
        }
    """
    config_path = CONFIG_DIR / "risk_weights.json"

    # 預設值
    default_config = {
        'keyword': 5.0,
        'multi_user': 3.0,
        'escalation': 2.0,
        'config_item': 5.0,
        'role_component': 3.0,
        'time_cluster': 2.0
    }

    if not config_path.exists():
        # 建立預設配置檔案
        self.save_risk_weights_config(default_config)
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 展平結構
            return {
                'keyword': data.get('severity', {}).get('keyword', 5.0),
                'multi_user': data.get('severity', {}).get('multi_user', 3.0),
                'escalation': data.get('severity', {}).get('escalation', 2.0),
                'config_item': data.get('frequency', {}).get('config_item', 5.0),
                'role_component': data.get('frequency', {}).get('role_component', 3.0),
                'time_cluster': data.get('frequency', {}).get('time_cluster', 2.0)
            }
    except Exception as e:
        log_error(f"Load risk weights config error: {e}")
        return default_config

def save_risk_weights_config(self, weights: Dict):
    """
    儲存細項權重配置

    Args:
        weights: {
            'keyword': 5.0,
            'multi_user': 3.0,
            'escalation': 2.0,
            'config_item': 5.0,
            'role_component': 3.0,
            'time_cluster': 2.0
        }

    Raises:
        ValidationError: 如果權重值 <= 0
    """
    # 驗證權重值
    for key, value in weights.items():
        if value <= 0:
            raise ValidationError(
                "INVALID_WEIGHT",
                f"權重值必須大於 0：{key} = {value}"
            )

    # 建立分組結構
    config_data = {
        "severity": {
            "keyword": weights.get('keyword', 5.0),
            "multi_user": weights.get('multi_user', 3.0),
            "escalation": weights.get('escalation', 2.0)
        },
        "frequency": {
            "config_item": weights.get('config_item', 5.0),
            "role_component": weights.get('role_component', 3.0),
            "time_cluster": weights.get('time_cluster', 2.0)
        }
    }

    config_path = CONFIG_DIR / "risk_weights.json"
    CONFIG_DIR.mkdir(exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    log_info(f"Risk weights config saved: {config_data}")
```

#### 1.3 新增細項權重 API

**檔案**: `services/config_service.py`

**新增方法**:
```python
def get_risk_weights(self) -> Dict:
    """
    取得細項權重配置

    Returns:
        {
            "severity": {
                "keyword": 5.0,
                "multi_user": 3.0,
                "escalation": 2.0
            },
            "frequency": {
                "config_item": 5.0,
                "role_component": 3.0,
                "time_cluster": 2.0
            }
        }
    """
    try:
        weights = self.config_loader.get_risk_weights_config()
        log_info(f"Retrieved risk weights: {weights}")

        # 重組為分組格式
        return {
            "severity": {
                "keyword": weights['keyword'],
                "multi_user": weights['multi_user'],
                "escalation": weights['escalation']
            },
            "frequency": {
                "config_item": weights['config_item'],
                "role_component": weights['role_component'],
                "time_cluster": weights['time_cluster']
            }
        }
    except Exception as e:
        log_error(f"Get risk weights error: {str(e)}")
        raise ValidationError("CONFIG_NOT_FOUND", "取得細項權重配置失敗")

def update_risk_weights(
    self,
    keyword: float,
    multi_user: float,
    escalation: float,
    config_item: float,
    role_component: float,
    time_cluster: float
) -> Dict:
    """
    更新細項權重配置

    Args:
        keyword: 高風險關鍵字權重
        multi_user: 多用戶影響權重
        escalation: 升級需求權重
        config_item: 配置項目頻率權重
        role_component: 角色元件頻率權重
        time_cluster: 時間聚類權重

    Returns:
        更新後的配置

    Raises:
        ValidationError: 如果任何權重 <= 0
    """
    # 驗證所有權重 > 0
    weights_to_validate = {
        'keyword': keyword,
        'multi_user': multi_user,
        'escalation': escalation,
        'config_item': config_item,
        'role_component': role_component,
        'time_cluster': time_cluster
    }

    for key, value in weights_to_validate.items():
        if value <= 0:
            raise ValidationError(
                "WEIGHT_INVALID",
                f"權重值必須大於 0：{key} = {value}",
                details={"weight": key, "value": value}
            )

    # 儲存配置
    weights = {
        'keyword': keyword,
        'multi_user': multi_user,
        'escalation': escalation,
        'config_item': config_item,
        'role_component': role_component,
        'time_cluster': time_cluster
    }

    try:
        self.config_loader.save_risk_weights_config(weights)
        log_info(f"Updated risk weights: {weights}")

        # 回傳分組格式
        return {
            "severity": {
                "keyword": keyword,
                "multi_user": multi_user,
                "escalation": escalation
            },
            "frequency": {
                "config_item": config_item,
                "role_component": role_component,
                "time_cluster": time_cluster
            }
        }
    except Exception as e:
        log_error(f"Update risk weights error: {str(e)}")
        raise ValidationError("CONFIG_UPDATE_ERROR", f"更新細項權重配置失敗: {str(e)}")
```

**檔案**: `api/config_routes.py`

**新增路由**:
```python
# ==================== Risk Weights Configuration ====================

@config_bp.route('/config/risk-weights', methods=['GET'])
def get_risk_weights():
    """
    Get risk weights configuration

    Returns:
        {
            "severity": {
                "keyword": 5.0,
                "multi_user": 3.0,
                "escalation": 2.0
            },
            "frequency": {
                "config_item": 5.0,
                "role_component": 3.0,
                "time_cluster": 2.0
            }
        }
    """
    try:
        config_service = get_service("config")
        weights = config_service.get_risk_weights()
        return jsonify(weights), 200

    except ValidationError as e:
        return make_error_response(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        log_error(f"Get risk weights error: {str(e)}")
        return make_error_response("CONFIG_NOT_FOUND", "取得細項權重配置失敗", status_code=500)


@config_bp.route('/config/risk-weights', methods=['POST'])
def update_risk_weights():
    """
    Update risk weights configuration

    Request Body:
        {
            "severity": {
                "keyword": 5.0,
                "multi_user": 3.0,
                "escalation": 2.0
            },
            "frequency": {
                "config_item": 5.0,
                "role_component": 3.0,
                "time_cluster": 2.0
            }
        }

    Or flat format:
        {
            "keyword": 5.0,
            "multi_user": 3.0,
            "escalation": 2.0,
            "config_item": 5.0,
            "role_component": 3.0,
            "time_cluster": 2.0
        }
    """
    try:
        data = request.json

        # 支援兩種格式
        if 'severity' in data and 'frequency' in data:
            # 分組格式
            keyword = data['severity'].get('keyword')
            multi_user = data['severity'].get('multi_user')
            escalation = data['severity'].get('escalation')
            config_item = data['frequency'].get('config_item')
            role_component = data['frequency'].get('role_component')
            time_cluster = data['frequency'].get('time_cluster')
        else:
            # 展平格式
            keyword = data.get('keyword')
            multi_user = data.get('multi_user')
            escalation = data.get('escalation')
            config_item = data.get('config_item')
            role_component = data.get('role_component')
            time_cluster = data.get('time_cluster')

        # 驗證必要參數
        if any(v is None for v in [keyword, multi_user, escalation, config_item, role_component, time_cluster]):
            raise ValidationError("INVALID_PARAMETER", "缺少必要的權重參數")

        config_service = get_service("config")
        weights = config_service.update_risk_weights(
            keyword, multi_user, escalation,
            config_item, role_component, time_cluster
        )

        return jsonify({
            "status": "success",
            "message": "細項權重配置已更新",
            "config": weights
        }), 200

    except ValidationError as e:
        return make_error_response(e.code, e.message, e.details, e.status_code)
    except Exception as e:
        log_error(f"Update risk weights error: {str(e)}", exc_info=True)
        return make_error_response("INTERNAL_SERVER_ERROR", "更新細項權重配置失敗", status_code=500)
```

#### 1.4 修改 TicketService 使用新的權重配置

**檔案**: `services/ticket_service.py`

**修改位置**: `_process_ticket_row()` 方法（約第 578 行）

**現有程式碼**:
```python
# Calculate composite scores using RiskService
severity_score, frequency_score, impact_score = (
    self.risk_service.calculate_risk_scores(
        keyword_score,
        user_impact_score,
        escalation_score,
        configuration_item_freq,
        role_component_freq,
        time_cluster_score
    )
)
```

**修改為**:
```python
# 讀取權重配置
from core import get_config_loader
config_loader = get_config_loader()

# 取得細項權重配置
risk_weights = config_loader.get_risk_weights_config()

# 取得總體權重配置
overall_weights = config_loader.get_weight_config()

# Calculate composite scores using RiskService (with weights)
severity_score, frequency_score, impact_score = (
    self.risk_service.calculate_risk_scores(
        keyword_score,
        user_impact_score,
        escalation_score,
        configuration_item_freq,
        role_component_freq,
        time_cluster_score,
        weights=risk_weights,
        overall_weights=overall_weights
    )
)
```

**注意事項**:
- 確保 config_loader 只初始化一次（可以在 __init__ 中初始化）
- 考慮快取權重配置，避免每筆工單都重新讀取檔案

### 驗收標準

- [ ] RiskService 計算邏輯正確使用總體權重
- [ ] 細項權重 API 可正常讀取和更新
- [ ] TicketService 正確呼叫新的計算邏輯
- [ ] 所有單元測試通過
- [ ] 不影響現有上傳分析功能
- [ ] config/risk_weights.json 正確建立

---

## 🎯 Phase 2: 風險語句管理 API (2-3 小時)

### 目標
提供管理 `data/sentences/*.json` 的 API 介面

### 任務清單

#### 2.1 新增語句管理工具函數

**檔案**: `utils/sentence_utils.py`

**新增方法**:
```python
def get_risk_sentences(category: str) -> List[str]:
    """
    取得指定類別的風險語句

    Args:
        category: high_risk, escalate, multi_user

    Returns:
        語句列表
    """
    filepath = os.path.join(DATA_DIR, f"{category}.json")

    if not os.path.exists(filepath):
        # 建立空檔案
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Load risk sentences error: {e}")
        return []

def add_risk_sentence(category: str, sentence: str) -> bool:
    """
    新增風險語句

    Returns:
        True if success
    """
    sentences = get_risk_sentences(category)

    if sentence in sentences:
        raise ValueError(f"語句已存在：{sentence}")

    sentences.append(sentence)

    filepath = os.path.join(DATA_DIR, f"{category}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)

    return True

def delete_risk_sentence(category: str, sentence: str) -> bool:
    """
    刪除風險語句
    """
    sentences = get_risk_sentences(category)

    if sentence not in sentences:
        raise ValueError(f"語句不存在：{sentence}")

    sentences.remove(sentence)

    filepath = os.path.join(DATA_DIR, f"{category}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)

    return True

def update_risk_sentence(category: str, old_sentence: str, new_sentence: str) -> bool:
    """
    更新風險語句
    """
    sentences = get_risk_sentences(category)

    if old_sentence not in sentences:
        raise ValueError(f"原語句不存在：{old_sentence}")

    if new_sentence in sentences and new_sentence != old_sentence:
        raise ValueError(f"新語句已存在：{new_sentence}")

    idx = sentences.index(old_sentence)
    sentences[idx] = new_sentence

    filepath = os.path.join(DATA_DIR, f"{category}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)

    return True
```

#### 2.2 新增 ConfigService 方法

**檔案**: `services/config_service.py`

**新增方法**:
```python
# ==================== Risk Sentences Management ====================

def get_risk_sentences(self, category: str) -> List[str]:
    """
    取得指定類別的風險語句

    Args:
        category: high_risk, escalate, multi_user

    Returns:
        語句列表
    """
    from utils.sentence_utils import get_risk_sentences as get_sentences

    valid_categories = ['high_risk', 'escalate', 'multi_user']
    if category not in valid_categories:
        raise ValidationError(
            "INVALID_PARAMETER",
            f"無效的類別：{category}，有效值為：{valid_categories}"
        )

    try:
        sentences = get_sentences(category)
        log_info(f"Retrieved {len(sentences)} sentences for category: {category}")
        return sentences
    except Exception as e:
        log_error(f"Get risk sentences error: {str(e)}")
        return []

def add_risk_sentence(self, category: str, sentence: str) -> Dict:
    """
    新增風險語句
    """
    from utils.sentence_utils import add_risk_sentence as add_sentence

    if not sentence or not sentence.strip():
        raise ValidationError("INVALID_PARAMETER", "語句不能為空")

    valid_categories = ['high_risk', 'escalate', 'multi_user']
    if category not in valid_categories:
        raise ValidationError(
            "INVALID_PARAMETER",
            f"無效的類別：{category}，有效值為：{valid_categories}"
        )

    try:
        add_sentence(category, sentence.strip())
        log_info(f"Added sentence to {category}: {sentence[:50]}...")
        return {"status": "success", "message": "語句已新增"}
    except ValueError as e:
        raise ValidationError("SENTENCE_EXISTS", str(e))
    except Exception as e:
        log_error(f"Add risk sentence error: {str(e)}")
        raise ValidationError("SENTENCE_ADD_ERROR", f"新增語句失敗: {str(e)}")

def delete_risk_sentence(self, category: str, sentence: str) -> Dict:
    """
    刪除風險語句
    """
    from utils.sentence_utils import delete_risk_sentence as delete_sentence

    try:
        delete_sentence(category, sentence)
        log_info(f"Deleted sentence from {category}: {sentence[:50]}...")
        return {"status": "success", "message": "語句已刪除"}
    except ValueError as e:
        raise ValidationError("SENTENCE_NOT_FOUND", str(e))
    except Exception as e:
        log_error(f"Delete risk sentence error: {str(e)}")
        raise ValidationError("SENTENCE_DELETE_ERROR", f"刪除語句失敗: {str(e)}")

def update_risk_sentence(
    self,
    category: str,
    old_sentence: str,
    new_sentence: str
) -> Dict:
    """
    更新風險語句
    """
    from utils.sentence_utils import update_risk_sentence as update_sentence

    if not new_sentence or not new_sentence.strip():
        raise ValidationError("INVALID_PARAMETER", "新語句不能為空")

    try:
        update_sentence(category, old_sentence, new_sentence.strip())
        log_info(f"Updated sentence in {category}")
        return {"status": "success", "message": "語句已更新"}
    except ValueError as e:
        raise ValidationError("SENTENCE_ERROR", str(e))
    except Exception as e:
        log_error(f"Update risk sentence error: {str(e)}")
        raise ValidationError("SENTENCE_UPDATE_ERROR", f"更新語句失敗: {str(e)}")
```

#### 2.3 新增 API 路由

**檔案**: `api/config_routes.py`

**新增路由**:
```python
# ==================== Risk Sentences Management ====================

@config_bp.route('/config/risk-sentences', methods=['GET'])
def get_risk_sentences():
    """
    Get risk sentences for category

    Query params:
        category: high_risk | escalate | multi_user

    Returns:
        {
            "category": "high_risk",
            "sentences": ["sentence1", "sentence2", ...]
        }
    """
    try:
        category = request.args.get('category', 'high_risk')

        config_service = get_service("config")
        sentences = config_service.get_risk_sentences(category)

        return jsonify({
            "category": category,
            "sentences": sentences
        }), 200

    except ValidationError as e:
        return make_error_response(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        log_error(f"Get risk sentences error: {str(e)}")
        return make_error_response("INTERNAL_SERVER_ERROR", "取得風險語句失敗", status_code=500)


@config_bp.route('/config/risk-sentences', methods=['POST'])
def add_risk_sentence():
    """
    Add risk sentence

    Request Body:
        {
            "category": "high_risk",
            "sentence": "system failure"
        }
    """
    try:
        data = request.json
        category = data.get("category")
        sentence = data.get("sentence")

        if not category or not sentence:
            raise ValidationError("INVALID_PARAMETER", "缺少必要參數")

        config_service = get_service("config")
        result = config_service.add_risk_sentence(category, sentence)

        return jsonify(result), 200

    except ValidationError as e:
        return make_error_response(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        log_error(f"Add risk sentence error: {str(e)}")
        return make_error_response("INTERNAL_SERVER_ERROR", "新增語句失敗", status_code=500)


@config_bp.route('/config/risk-sentences', methods=['DELETE'])
def delete_risk_sentence():
    """
    Delete risk sentence

    Request Body:
        {
            "category": "high_risk",
            "sentence": "system failure"
        }
    """
    try:
        data = request.json
        category = data.get("category")
        sentence = data.get("sentence")

        config_service = get_service("config")
        result = config_service.delete_risk_sentence(category, sentence)

        return jsonify(result), 200

    except ValidationError as e:
        return make_error_response(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        log_error(f"Delete risk sentence error: {str(e)}")
        return make_error_response("INTERNAL_SERVER_ERROR", "刪除語句失敗", status_code=500)


@config_bp.route('/config/risk-sentences', methods=['PUT'])
def update_risk_sentence():
    """
    Update risk sentence

    Request Body:
        {
            "category": "high_risk",
            "old_sentence": "system failure",
            "new_sentence": "critical system failure"
        }
    """
    try:
        data = request.json
        category = data.get("category")
        old_sentence = data.get("old_sentence")
        new_sentence = data.get("new_sentence")

        config_service = get_service("config")
        result = config_service.update_risk_sentence(category, old_sentence, new_sentence)

        return jsonify(result), 200

    except ValidationError as e:
        return make_error_response(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        log_error(f"Update risk sentence error: {str(e)}")
        return make_error_response("INTERNAL_SERVER_ERROR", "更新語句失敗", status_code=500)
```

#### 2.4 確保 data/sentences/ 目錄存在

**檔案**: `utils/sentence_utils.py`

**修改 DATA_DIR 初始化**:
```python
import os

DATA_DIR = "data/sentences"

def ensure_sentences_directory():
    """確保 data/sentences/ 目錄存在，並建立預設檔案"""
    os.makedirs(DATA_DIR, exist_ok=True)

    categories = ['high_risk', 'escalate', 'multi_user']
    for category in categories:
        filepath = os.path.join(DATA_DIR, f"{category}.json")
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

# 模組載入時自動確保目錄存在
ensure_sentences_directory()
```

### 驗收標準

- [ ] 可以讀取、新增、刪除、更新風險語句
- [ ] data/sentences/ 目錄不存在時自動建立
- [ ] API 回應格式正確
- [ ] 錯誤處理完善（語句重複、語句不存在等）
- [ ] 不影響 SmartScoring 的語句載入

---

## 🎯 Phase 3: 前端系統設定頁面開發 (5-7 小時)

### 目標
建立統一的系統設定頁面，整合所有設定功能

### 3.1 建立系統設定頁面模板

**新檔案**: `templates/system_settings.html`

詳細內容請參考實作時展開...

### 3.2 建立樣式檔案

**新檔案**: `static/css/system_settings.css`

### 3.3 建立 JavaScript 檔案

**新檔案**: `static/js/system_settings.js`

### 3.4 建立路由

**檔案**: `api/page_routes.py`

（詳細內容省略，實作時補充）

---

## 🎯 Phase 4: 移除舊功能與整合 (2-3 小時)

（詳細內容省略）

---

## 🎯 Phase 5: 測試與驗證 (2-3 小時)

（詳細內容省略）

---

## 📊 時程估算

| Phase | 預估時間 | 累計時間 |
|-------|---------|---------|
| Phase 1: 後端邏輯修正 | 3-5 小時 | 3-5 小時 |
| Phase 2: 語句管理 API | 2-3 小時 | 5-8 小時 |
| Phase 3: 前端頁面開發 | 5-7 小時 | 10-15 小時 |
| Phase 4: 移除舊功能 | 2-3 小時 | 12-18 小時 |
| Phase 5: 測試驗證 | 2-3 小時 | 14-21 小時 |

**總計**: 14-21 小時（約 2-3 個工作天）

---

## ⚠️ 風險與注意事項

### 高風險項目

1. **RiskService 計算邏輯修改**
   - 影響範圍：所有工單的風險評分
   - 緩解措施：完整的單元測試 + 迴歸測試
   - 向後相容策略：overall_weights=None 時使用舊公式

2. **移除 gpt_prompt 頁面**
   - 影響範圍：依賴此頁面的功能
   - 緩解措施：確認無其他功能呼叫此路由
   - 檢查項目：base.html 導航、所有 JS 檔案的 navigateTo1() 呼叫

3. **API 路由衝突**
   - 影響範圍：現有 API 可能被覆蓋
   - 緩解措施：使用新的路由前綴 `/api/config/risk-*`
   - 檢查項目：確保新路由不與現有路由衝突

### 向後相容策略

1. **保留現有 API 端點**
   - `/api/config/weight` 保持不變
   - 新增 `/api/config/risk-weights` 作為細項權重端點
   - RiskService.calculate_risk_scores() 保持向後相容

2. **漸進式遷移**
   - 先完成後端邏輯，確保計算正確
   - 再移除前端舊介面
   - 最後進行文檔更新

3. **測試覆蓋**
   - 所有修改的模組都有對應的單元測試
   - 整合測試覆蓋完整的使用流程

---

## ✅ 驗收檢查清單

### 功能完整性

- [ ] 系統設定頁面正常運作
- [ ] 風險評估設定（總體權重 + 細項權重 + 語句管理）完整
- [ ] AI 模型設定（Prompt + 模型）完整
- [ ] 舊功能完全移除（gpt_prompt 頁面、分群頁面權重配置）
- [ ] 導航連結更新完成

### 程式碼品質

- [ ] 所有單元測試通過（覆蓋率 > 90%）
- [ ] 所有整合測試通過
- [ ] 無 Python linting 錯誤
- [ ] 無 JavaScript console 錯誤
- [ ] 程式碼遵循專案規範

### 使用者體驗

- [ ] UI 風格與現有頁面一致
- [ ] 表單驗證清晰友善
- [ ] 錯誤訊息有幫助
- [ ] 響應式設計正常
- [ ] 載入速度快（< 1s）

### 文檔完整性

- [ ] CLAUDE.md 已更新
- [ ] 完成報告已建立
- [ ] API 文檔已更新

---

## 📝 實施注意事項

### 開發順序

1. **先做後端，後做前端**（按照用戶要求）
2. **小步快跑，頻繁測試**
3. **每個 Phase 完成後 commit**

### Git Commit 建議

```bash
# Phase 1
git commit -m "feat(risk): modify RiskService to use overall weights config"
git commit -m "feat(config): add risk weights management in config_loader"
git commit -m "feat(api): add risk weights management API endpoints"
git commit -m "refactor(ticket): integrate risk weights config in TicketService"

# Phase 2
git commit -m "feat(utils): add risk sentences management utilities"
git commit -m "feat(api): add risk sentences management API endpoints"

# Phase 3
git commit -m "feat(ui): add system settings page template"
git commit -m "feat(ui): add system settings CSS and JS"
git commit -m "feat(api): add system settings page route"

# Phase 4
git commit -m "refactor(ui): remove weight config from cluster page"
git commit -m "refactor: remove gpt_prompt page and integrate to system_settings"
git commit -m "refactor(nav): update navigation links to system_settings"

# Phase 5
git commit -m "test: add comprehensive tests for system settings features"
git commit -m "test: add regression tests for risk calculation"
git commit -m "docs: update CLAUDE.md for system settings integration"
git commit -m "docs: add completion report for Phase 1-5"
```

### 測試策略

- 每完成一個 Phase，執行對應的測試
- Phase 5 之前不要合併到 main 分支
- 使用 feature branch: `feature/system-settings-integration`

---

## 📅 執行時程表

| 日期 | Phase | 預期完成 |
|------|-------|---------|
| 2025-11-22 | Phase 1 | 後端邏輯修正完成 |
| 2025-11-23 | Phase 2 | 語句管理 API 完成 |
| 2025-11-24 | Phase 3 | 前端頁面開發完成 |
| 2025-11-25 | Phase 4 + 5 | 移除舊功能、測試驗證完成 |

---

**計畫建立者**: Claude Code
**計畫日期**: 2025-11-22
**預計完成日期**: 2025-11-25
**狀態**: 執行中

**最後更新**: 2025-11-22 (計畫建立)

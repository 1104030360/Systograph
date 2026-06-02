# Future: Multimodal RAG Fixture and Scanner Support

## 來源
Task 4 (Build Test Fixtures and Contract Baseline) 在多處提到 multimodal 是重要但延後的方向：

> | `HKUDS/RAG-Anything` | Multimodal RAG | 多模態重要，但 Task 4 初版可先不做 |

> 第一版可以先延後的階段：
> - multimodal ingestion

> multimodal fixtures 可以先做 optional，避免 Task 4 一次變成大型資料集工程。

## 目的
擴充 scanner 支援 multimodal RAG 系統（影像、音訊、影片等非文字資料的 ingestion、embedding、retrieval）。

## 觸發條件
- 使用者的 RAG 系統包含 image / audio / video ingestion pipeline。
- 需要偵測 multimodal embedding model（例如 CLIP、ImageBind）。
- 需要辨識 multimodal document loader（例如 Unstructured、LlamaParse for images）。

## 建議範圍
- 建立 `multimodal_rag/` test fixture。
- 參考 `HKUDS/RAG-Anything` 的 multimodal pipeline pattern。
- 擴充 scanner rules 支援 multimodal-specific dependencies 與 config。
- 擴充 template slots 或 extension components（若 `rag-core-v1` 不足以表達 multimodal）。
- Fixture 不可包含真實影像/音訊/影片資料，只放 scanner signals。

## 與既有任務關係
- Task 4：已建立 fixture 框架與 provider coverage matrix。
- Task 11：code pattern provider 可能需要新增 multimodal import pattern。
- Task 13：component detection 可能需要新增 multimodal component 類型。
- Task 24：final review 可評估 multimodal support gap。

## 不做事項
- 不建立完整 multimodal pipeline runner。
- 不放真實影像、音訊、影片檔案進 fixtures。
- 不做 multimodal model inference。

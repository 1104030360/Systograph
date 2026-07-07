# RAG 共同架構：從 Naive/Modular 到 2026 Agentic・Graph・Memory 的統一設計視角
## 概覽
本報告整理 2023–2026 年間關於 Retrieval-Augmented Generation（RAG）的主要綜述與新架構論文，結合使用者提供的「RAG 系統設計地圖」Markdown 文件，嘗試給出一個實務導向的「共同架構」視角：哪些部分可以視為所有現代 RAG 系統的共通骨架，哪些則是可疊加的模組或特定應用變體。[1][2]

核心結論是：

- **Naive / 2-Step RAG** 只是一個最小 primitive（index → retrieve → generate），不適合作為 2026 之前沿 RAG 系統的「共同架構」代表。[2][1]
- **Modular RAG** 比較符合共同骨架的角色：它將檢索、路由、生成等拆解成可替換模組，能承載後續 Agentic、Graph、Memory 等高階變體。[1][2]
- 2026 一系列工作（A-RAG、Agentic GraphRAG、Infini Memory、RAG-Anything）可以理解成在 Modular 骨架上分別加上「控制層」「圖結構層」「長期記憶層」「多模態知識層」。[3][4][5][6]
- Anthropic 的 Contextual Retrieval、Hybrid Retrieval、Reranking、Query Rewriting 等，應被視為 **橫向可疊加元件（cross-cutting components）**，而非獨立架構；它們可以插入任何 Naive/Advanced/Modular/Agentic/Graph pipeline 中。[7][1]

以下依層級與設計面向展開說明，並對「RAG 共同架構」給出一個可操作的定義。

***
## 一、基礎：Naive / Advanced / Modular 三階演進
### 1.1 Naive RAG 作為 Core Primitive
早期綜述（Gao et al., 2023/2024）將 Naive RAG 定義為最簡單的兩步流程：對查詢做向量化，檢索 top-k 文本片段，將之拼接進 prompt 再交由 LLM 生成答案。 在使用者提供的系統設計地圖中，這個 primitive 被放在 **Layer 1：Core Primitive**，作為所有變體的底層最小執行單元。[1][2]

這種 Naive RAG 的特徵：

- 單次線性 pipeline：`retrieve → augment → generate`，缺乏查詢改寫、重排序或檢索品質檢查。
- 檢索策略通常是單一密集向量檢索（例如 cosine similarity on embeddings）。
- 沒有反思迴圈、路由決策或長期記憶操作，故無法捕捉現代 Agentic 或多輪推理場景。[2]

因此，Naive RAG 在現代框架中較適合被視為「基礎積木」，而非完整共同架構。
### 1.2 Advanced RAG：在固定管線中插入優化模組
Advanced RAG 在 Naive primitive 前後加入若干強化步驟，如 query rewriting、multi-query retrieval、hybrid retrieval（稀疏+稠密）、reranking 等。 使用者文件將其放在 **Layer 2：Common Framework**，但仍視為「固定管線」型主架構。[1][8][2]

共通特徵：

- 仍然是 **單條 pipeline**，但每個階段更精緻，例如：`rewrite query → hybrid retrieve → rerank → generate`。
- 還未完全把各步驟抽象成獨立模組，多半是具體實作上「插入幾個強化 component」。
- 適合作為入門到中階實務系統的藍本，但在支援 Agentic/多路選擇方面仍有侷限。[2]
### 1.3 Modular RAG：共同骨架與「LEGO 化」設計
Modular RAG（Gao et al., 2024）被描述為「將 RAG 系統轉換成 LEGO 式可重構框架」：檢索器、路由器、生成器、反思模組被拆成獨立元件，彼此透過明確的介面與條件分支串接。 使用者設計地圖特別將 Modular RAG標註為「共同骨架，系統框架，高度可組合」，並指出它能支撐後續 Agentic RAG、GraphRAG 等高階變體。[1][2]

Modular RAG 作為共同架構的關鍵理由：

- **抽象程度適中**：既保留 `index → retrieve → generate` 的基本骨架，又允許插入查詢理解、控制迴圈、證據處理等模組。
- **支援條件分支與迴圈**：可以表達「如果答案不確定則觸發額外檢索」「若檢索結果衝突則啟用辯論模組」這類控制邏輯。[2][1]
- **與 Agentic/Graph/Memory 自然相容**：A-RAG 的階層式檢索介面、Agentic GraphRAG 的分析型 agent、Infini Memory 的 topic-document 檢索，都可以作為 Modular pipeline 中的特定模組實例。[4][5][6]

因此，報告採用使用者文件的結論：**在 2026 RAG 技術版圖下，Modular RAG 是最合理的「共同架構」骨架，而 Naive RAG 是其底層 primitive。**[1]

***
## 二、RAG 四層模型與共同架構視角
使用者提供的 Markdown 將現代 RAG 概念整理成「四層模型」，這個模型很適合用來定義共同架構的範圍。[1]

```text
Layer 1：Core Primitive
  - Naive / 2-Step RAG

Layer 2：Common Framework
  - Advanced RAG
  - Modular RAG

Layer 3：Cross-cutting Components
  - Hybrid Retrieval
  - Contextual Retrieval
  - Reranking
  - Query Rewriting
  - Multi-query Retrieval
  - RAGLAB

Layer 4：Higher-level Variants
  - Query Understanding
  - Control & Reasoning
  - Knowledge Structure
  - Evidence Reliability
  - Multimodal / Semi-structured
  - Memory-augmented RAG
  - Collaborative / Federated RAG
```
### 2.1 共同架構的「垂直範圍」
從此四層模型出發，可以定義：

- **共同骨架主要落在 Layer 1 + Layer 2**：即 Naive primitive 與 Advanced/Modular framework。
- **Layer 3 是橫向可疊加元件**：可插入任何骨架中，不改變骨架本身；因此不應被視為共同架構的一部分，而是 plugin 層。
- **Layer 4 是高階變體與場景特化層**：Agentic、Graph、Memory、Multimodal 等，必須建立在共同骨架之上才有意義。[1][2]

換句話說，RAG 的共同架構可以被理解為：

1. 一個最小 `retrieve → augment → generate` primitive（Naive）。
2. 一個支援模組化組裝、條件分支與迴圈的骨架（Modular RAG）。
3. 在此骨架上，可以插入或關閉 Layer 3 的橫向元件（contextual retrieval、reranking 等）。
4. Layer 4 的高階變體則視為「在共同架構上，附加不同維度的能力」。
### 2.2 端到端共同流程圖
使用者文件提供的「端到端共同流程圖」本質上就是對共同架構各層的抽象化描述：[1]

```text
User Query
   ↓
Query Understanding
   ├── Typed-RAG
   ├── MRAG
   └── Query Rewriting / Multi-query Retrieval
   ↓
Control Layer
   ├── Fixed Pipeline
   ├── Corrective Control
   └── Agentic / Reasoning Control
   ↓
Retrieval Layer
   ├── Dense Retrieval
   ├── Hybrid Retrieval
   ├── Graph Retrieval
   ├── Multimodal Retrieval
   └── Memory Retrieval
   ↓
Evidence Layer
   ├── Reranking
   ├── Conflict Resolution
   └── Evidence Validation
   ↓
Context Construction & Generation
   ↓
Memory Update / Feedback Loop
```

在這張圖裡，**共同架構的本質是：所有現代 RAG 系統都可以被映射到這些層級上，只是各層選用的具體技術不同。**例如：

- 傳統 Naive RAG：幾乎只有「Retrieval Layer（Dense）」與「Context Construction & Generation」兩層存在，且缺乏 Query/Evidence/Memory 層的精細處理。
- 一般 Advanced RAG：在 Query Understanding 層加入 query rewriting、多 query，在 Evidence 層加入 Cross-encoder reranking。[8][9]
- A-RAG：強化 Control Layer，讓 agent 自主選擇 keyword search / semantic search / chunk read 等工具。[5][10]
- Agentic GraphRAG：在 Knowledge Structure 層選擇 Graph Retrieval，並在 Control Layer 使用 modular agent 管理圖訪問與反思迴圈。[4]
- Infini Memory：在 Memory Retrieval 層引入 topic-structured documents 與 iterative memory inspection，並在 Memory Update 層加入維護流程。[6][11]

這種層級化視角使得「共同架構」不再是某一種特定 pipeline，而是一組 **必要設計維度**：任何稱得上現代 RAG 系統的架構，都應該能在這張流程圖上找到自己的定位。

***
## 三、Cross-cutting Components：不屬於共同架構但幾乎必備的插件
使用者文件明確將 Hybrid Retrieval、Contextual Retrieval、Reranking、Query Rewriting、Multi-query Retrieval、RAGLAB 歸類為「橫向可疊加元件」，並強調它們不是獨立主架構。 這與外部資料相符：[1]

- Anthropic 的 Contextual Retrieval 被定位為一種索引前處理與檢索改寫技術，透過 contextual embeddings 與 contextual BM25 將 chunk 補上上下文，並搭配 reranking 至多可降低 top-20 retrieval failure rate 67%。[7][12]
- Hybrid Retrieval 被各種教學與綜述視為「在稀疏與稠密檢索之間做融合」，通常使用 RRF 或類似策略來融合 BM25 與向量相似度結果。[8][9]
- Reranking 使用 Cross-encoder 對 query–chunk pair 做精細打分，在 production RAG 教學中被視為「效益最大、成本可控」的必要元件。[9][8]
- Query Rewriting / Multi-query Retrieval 多半是 query understanding 層的優化，而非獨立架構，目的是提升召回覆蓋率。[9]
- RAGLAB 是 EMNLP 2024 的 demo framework，提供統一的 modular RAG 研究環境，協助分析不同組合的效能與穩定性。[13][14]

因此，從共同架構觀點看：

- 這些元件 **應被視為 plugin**，可以任意插入 Modular 骨架的不同位置。
- 它們不定義新的「RAG 類型」，但幾乎是高品質 RAG pipeline 的標準配備。
- 在設計共同架構時，應關注的是「如何在骨架中標準化這些元件的接口與插入點」，而非把它們納入類型分類樹。

***
## 四、Higher-level Variants：共同架構之上的七大維度
使用者文件把 RAG 高階變體拆成七個維度，對 2026 最新研究做了系統性整理：[1]

1. Query Understanding（查詢理解與分解）
2. Control & Reasoning Layer（控制與推理層）
3. Knowledge Structure（知識結構層）
4. Evidence Reliability（證據品質與衝突處理）
5. Multimodal / Semi-structured（多模態與半結構化）
6. Memory-augmented RAG（長期記憶型 RAG）
7. Collaborative / Federated RAG（協作式 / 聯邦式）

這些維度可以被看作「在共同骨架上加蓋樓層」，以下分別說明其代表性工作與與共同架構的關係。
### 4.1 Query Understanding：Typed-RAG、MRAG 等
此維度聚焦於如何在檢索前處理使用者查詢：

- **Typed-RAG**：先判斷查詢類型（如列舉、比較、因果）再選擇合適的檢索與生成策略模板。[1]
- **Multi-Head RAG (MRAG)**：利用 Transformer 不同注意力頭的多面向嵌入，為同一 query 產生多組 embedding，提升語意覆蓋。[1]

在共同架構中，這一維度主要影響 **Query Understanding 層**，屬於骨架的上游處理。其設計重點是如何將這些 typed routing 與 MRAG embedding 抽象成通用接口，好讓下游 Control/Retrieval 層不必知道查詢細節。
### 4.2 Control & Reasoning：Self-RAG、CRAG、MCTS-RAG、Agentic RAG、A-RAG
控制與推理層是 2024–2026 RAG 發展的主戰場，重點在於打破單次固定 pipeline：

- **Self-RAG**：在生成過程插入反思 token，自我判斷是否需要新增檢索，並檢查生成是否有證據支持。[1]
- **Corrective RAG (CRAG)**：在檢索之後評估 evidence 品質，如果不足則觸發 fallback 搜尋或查詢重寫，形成糾錯迴圈。[15][1]
- **ReaRAG**：推理與檢索交錯，每個推理節點決定「繼續思考」或「補查資料」。[1]
- **MCTS-RAG**：將檢索路徑視為樹狀搜尋，使用蒙地卡羅模擬來選擇最佳回答路徑，適合高複雜度問題。[15][1]
- **Agentic RAG（廣義）**：泛指由 agent 自主決定何時檢索、呼叫哪些工具的框架，常使用 ReAct-style Thought/Action/Observation 模式。[9][15]
- **A-RAG（2026）**：Du 等提出的階層式 Agentic RAG，暴露 keyword search、semantic search、chunk read 三種檢索工具給模型，讓其自主選擇並多輪使用。[5][10]

在共同架構視角下：

- 控制與推理層是 **Modular 骨架的一個核心模組群**，負責 orchestrate 各 plugin（Hybrid、Contextual、Graph 等）與 primitive（Naive retrieve + generate）。
- A-RAG 的 hierarchical retrieval interface 提供一個具體實作，說明如何設計工具接口，使 agent 能以最小約束自由組合檢索行為。[5]
- 從共同架構角度出發，重要的是抽象出「控制 API」與「工具簽名」，讓不同 Agentic 風格（Self-RAG、CRAG、MCTS-RAG、A-RAG）都能插入同一骨架。
### 4.3 Knowledge Structure：GraphRAG、Agentic GraphRAG、LightRAG、HeteRAG、Tree RAG、RAG-Anything 的圖層
知識結構層重構了 RAG 的索引邏輯：從扁平 chunk 切換到圖譜或樹狀結構。[1]

代表性工作：

- **GraphRAG**：將文件轉為實體與關係的知識圖譜，支援社群摘要、路徑推理回答全域問題。[4][1]
- **Agentic GraphRAG（Capozzi & Helbing, 2026）**：在圖索引之上加入 analytical modular agent，包含意圖路由、反思迴圈、工具式圖訪問與人類監督 dashboard。[4]
- **LightRAG**：雙層圖檢索架構，平衡建圖成本與高層主題摘要能力。[16][17]
- **Tree / Hierarchical RAG（如 RAPTOR 系列）**：透過遞迴聚類與摘要形成樹狀索引，允許按抽象層級檢索。[15][1]
- **HeteRAG**：針對異質資料庫建立統一異質圖索引，打通不同格式來源。[1]
- **RAG-Anything**：同時引入 cross-modal knowledge graph 作為多模態知識結構層，透過 dual-graph 連結文本語意與跨模態關係。[3][17]

共同架構觀點：

- 知識結構層決定「Retrieval Layer」使用的是 vector store 還是 graph/tree/hypergraph。
- GraphRAG/LightRAG/HeteRAG 等提供了具體 graph 索引實作，Agentic GraphRAG說明如何在這層上再疊加 Control & Reasoning 層的 agent。[4]
- 在共同骨架設計中，應對「索引與檢索接口」做抽象，以容納 vector-based 與 graph-based 索引，並讓控制層能以統一方式呼叫。
### 4.4 Evidence Reliability：MADAM-RAG、Conflict-aware RAG
此維度聚焦於 evidence 層的品質與衝突處理：

- **MADAM-RAG**：使用多 agent 辯論機制，分別代表不同資料源或觀點，透過辯論與仲裁處理衝突證據。[1]
- **Conflict-aware RAG**：偵測檢索片段間的矛盾，根據時效性或來源權重做裁決，甚至直接輸出多方觀點而非單一答案。[1]

在共同架構中，這層主要作用在 **Evidence Layer**，與 reranking 層平行。設計上重點是：

- 抽象出 evidence 評估與辯論的接口，允許插入不同實作（純打分、辯論、fact checking）。
- 與 Control Layer 積極互動：如果 evidence 評估結果顯示不可靠，控制層應能觸發額外檢索或更換資料源。
### 4.5 Multimodal / Semi-structured：Multimodal RAG、RAG-Anything
多模態與半結構化資料方面，代表性工作為：

- **Multimodal RAG**：利用多模態 embedding 處理圖片與表格，支援跨模態相似度檢索。[1][3]
- **RAG-Anything（HKUDS）**：提出 dual-graph 架構，同時處理文本、圖片、表格、公式，透過 multimodal parsing + cross-modal knowledge graph + hybrid retrieval 三階段實現多模態 RAG。[18][3][17]

共同架構視角下：

- 多模態維度主要影響 **Knowledge Structure 層**（建 graph）與 **Retrieval Layer**（multimodal retrieval）。
- RAG-Anything 在實務中提供了一個「所有文檔統一進線」的框架，可視為在 Modular 骨架上，加上多模態 parsing 與 dual-graph 插件。[3][17]
### 4.6 Memory-augmented RAG：Long-term Memory RAG、Infini Memory
長期記憶型 RAG 是 2026 新興領域，代表性工作為 Infini Memory：[6]

- Infini Memory 將 agent memory 視為 topic-structured documents，每個 topic document 收集相關證據與 metadata，支援事後事實修訂與維護。[19][6]
- 新 observation 先進入 buffer，再定期整理進主題文件；推論時透過 agentic retrieval 程序多輪讀取記憶，而非單次檢索。[6]

共同架構視角：

- Memory 層可視為「一個專門針對長期資料的 RAG 系統」，其骨架仍然是 Modular RAG，只是資料源與更新流程不同。[1][6]
- Infini Memory 說明了如何把 memory 抽象成 topic documents 並與 agentic retrieval整合，提供共同架構設計上的參考：記憶不再是一個 vector store，而是一組可維護的主題文檔。
### 4.7 Collaborative / Federated：CoRAG
協作式 RAG 代表跨客戶端、跨組織的 RAG 設計：

- **CoRAG**：在多客戶端設定下共同訓練 retriever 與 reader，使用 CRAB benchmark 評估；關鍵在 collaborative passage store 的組成（包含 relevant passages、hard negatives、irrelevant passages）以及 FedAvg 聚合。[20][21]

在共同架構視角中：

- CoRAG 改變的是「系統如何被訓練與部署」，而非單一 pipeline；骨架仍可用 Modular RAG 表達，只是 passage store 與模型參數更新被分散到多客戶端。
- 因此共同架構應提供支援 federated training 與 collaborative passage store 的抽象，而非直接把 CoRAG視為另一類 pipeline。

***
## 五、2026 四大進化方向與共同架構的擴展
使用者文件在第 5 節總結了 2026 年 RAG 的四大趨勢，與外部文獻對應良好：[1]

1. Agentic Retrieval 正式化（A-RAG）。[5][10]
2. GraphRAG + Agentic 合流（Agentic GraphRAG）。[4]
3. Long-term Memory RAG 崛起（Infini Memory）。[6][11]
4. Multimodal Knowledge RAG（RAG-Anything）。[3][17]

這四大方向本質上都是在 Modular 骨架上加蓋不同維度的能力：

- A-RAG 強化 Control & Reasoning 層對檢索工具的操作，讓模型直接參與 retrieval decision。[5]
- Agentic GraphRAG 將 Graph-based knowledge structure 與 analytical agent 控制整合成一個協作框架。[4]
- Infini Memory 把 Memory 層升級為 topic-structured、可維護的長期 RAG 子系統。[6]
- RAG-Anything 把 Multimodal parsing 與 dual-graph 索引整合進 Knowledge Structure 層，解除文本-only RAG的限制。[17][3]

因此，從共同架構設計的角度，2026 的重點不在於創造一個全新的「共同架構名稱」，而是：

- 把 Modular RAG 的抽象程度提升到足以容納 Agentic/Graph/Memory/Multimodal 這些維度。
- 在骨架中明確標示 Query/Control/Retrieval/Evidence/Context/Memory 各層的接口與責任。
- 為 cross-cutting components（Contextual Retrieval、Hybrid、Reranking 等）設計標準插件介面。

***
## 六、RAG 共同架構的精確定義與層次關係
結合綜述與使用者文件，報告採用以下層次關係作為對「RAG 共同架構」的精確表述：[1][2]

```text
Agentic / Graph / Memory / Multimodal RAG（2026 新架構群）
└── 控制與結構層：由 Agent 決定何時檢索、讀取圖譜或操作長期記憶
    ↓
Modular RAG（共同骨架）
└── 可重新組裝、可分支、可循環的模組框架
    ↓
Naive RAG（最小單元）
└── 單次執行的 index → retrieve → generate
```

在這個視角下：

- **Naive RAG** 是所有 RAG 的最底層 primitive，定義了檢索+生成的基本操作單位。[2]
- **Modular RAG** 是現代 RAG 系統的共同骨架，抽象出 pipeline 中的模組與控制結構，支援多路由、多迴圈、多資料源。[1][2]
- **Agentic / Graph / Memory / Multimodal / Collaborative 等 2026 架構** 則是「在共同骨架上加上額外維度的專門子系統」，例如 A-RAG 專門擴展控制層，Infini Memory 專門擴展記憶層，RAG-Anything 專門擴展多模態知識結構層。[3][5][6]

最終判斷：

- **RAG 的共同架構不應被簡化為某一個具體 pipeline（如 Naive）或某一個命名變體（如 Agentic RAG）。**
- 更精確的說法是：**Modular RAG 提供了一個能表達 Query/Control/Retrieval/Evidence/Context/Memory 等層的統一骨架；2026 的各種新變體則是在這個骨架上填充不同維度的能力。**[2][1]

***
## 七、對系統設計者的實務建議
基於上述共同架構視角，對想實作 2026 世代 RAG 系統的工程師與研究者，可以給出以下設計建議：

1. **把核心實作先抽象成 Modular 骨架**：將 Query Understanding、Control、Retrieval、Evidence、Context、Memory 層抽象成獨立模組與明確接口，再決定每一層要用哪種具體技術（Naive vs Hybrid vs Graph vs Memory）。[1][2]
2. **先選一組 baseline plugin**：例如在 Retrieval 層使用 Hybrid Retrieval 并加上 Cross-encoder reranking，在 Query 層使用 query rewriting，在 Evidence 層加入基本 conflict checking。[8][7]
3. **再按需求加樓層**：如果問題多為開放式長期對話，就加 Infini Memory；如果多為文件密集且多模態，優先整合 RAG-Anything 或類似多模態框架；如果需要跨多 dataset 或組織，考慮 CoRAG 式 federated 設計。[3][6][21]
4. **不要把 plugin 當成類型**：Contextual Retrieval、Hybrid、Reranking、Multi-query 等應被配置成骨架中的可替換元件，而非在分類樹上與 Agentic RAG、GraphRAG並列，避免概念混淆。[7][1]
5. **留意命名衝突與演化**：例如 CoRAG 在不同年份被用於 Collaborative 與 Cooperative RAG，不同論文對 Agentic RAG 的定義也存在差異；共同架構設計時要明確標註版本與來源，避免混用。[20][22]

透過這種共通骨架+多維度變體的視角，可以在不犧牲嚴謹性的前提下，為實務系統設計提供清晰的地圖，也讓日後新提出的 RAG 變體有明確的「插入點」與對應層級。
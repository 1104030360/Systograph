# 2026 視角下的 RAG 共同架構：對原始設計地圖的驗證與修正
## 概覽
本報告以你提供的「RAG 系統設計地圖 — 多層架構解析與 2026 最新進展」為基準，結合 2023–2026 年最新綜述與代表性論文（Modular RAG、Reasoning Agentic RAG survey、A-RAG、Infini Memory、RAG-Anything 等），從「共同架構」的角度檢查其分類與層次是否成立，並在必要處提出修正意見。[1][2][3][4][5][6]

結論是：

- 對於 **Naive / Advanced / Modular** 的演化主幹，以及將 Hybrid Retrieval、Contextual Retrieval、Reranking、Query Rewriting 視為 **橫向可疊加元件**（而非獨立架構），你的地圖與最新文獻高度一致，甚至可以說是 state-of-the-art 的整理。[7][8][1]
- 將整個 RAG 技術版圖拆成「四層模型 + 九個設計維度」（Core Primitive、Common Framework、Cross-cutting Components、Query Understanding、Control & Reasoning、Knowledge Structure、Evidence Reliability、Multimodal、Memory、Collaborative），在 2026 的論文脈絡下是合理且有前瞻性的。[2][3][4][1]
- 可以反駁與補強的地方主要集中在三點：
  1. **Modular RAG 是否唯一可稱為『共同骨架』**：綜述中雖然給予 Modular 高度地位，但仍保留 Naive/Advanced 作為概念基石，實務上還存在一些非完全 modular 但高度 agentic 的框架，需加一句「在目前文獻中，Modular 是最適合作為共同骨架的候選，但不是唯一合法描述」。[9][2]
  2. **CoRAG 的定位與名稱歧義**：你把 CoRAG視為「協作式 RAG、Distributed Retrieval、獨立生態」，這在 2025 CoRAG 論文中是成立的，但 2026 又出現了以「Cooperative RAG」命名的工作，建議在設計地圖中標明這種命名衝突，避免後續讀者混淆。[10][11][12]
  3. **Agentic / Graph / Memory RAG 被視為『在 Modular 上加樓層』的表述略帶主觀色彩**：文獻中有些工作（如 RAG-Anything、Infini Memory）更偏向「獨立框架 + 提供一組可插入現有系統的工具鏈」，與「僅是 Modular 上的 extension」略有差異，可以補充這種雙重角色。

以下分段討論每一塊：驗證、肯定你 md 的設計選擇，並在局部提出具體修正建議。

***
## 一、Naive / Advanced / Modular：共同架構主幹的驗證
### 1.1 你對 Naive RAG 的定位
原始 md 把 Naive / 2-Step RAG 放在「0. Core Primitive」層，並明確寫出：

> Naive RAG 是最小可執行單元，不是現代 RAG 的完整共同架構。

這與 Gao 等人的綜述完全一致；該綜述將 Naive 定義為 `retrieve → augment → generate` 的線性兩步式 pipeline，並指出 Naive 無法涵蓋後續衍生的大量變體。[1][7]

因此，將 Naive 降格為「primitive 而不是共同骨架」是合理且與主流研究契合的，不需要修正。
### 1.2 Advanced RAG 與 Common Framework 的關係
你的地圖將 Advanced RAG 放在 Layer 2：Common Framework，描述為「在 Naive 前後加入查詢改寫、混合檢索、重排序等優化，但依然維持相對固定的線性管線」。[1]

在 Gao 等的綜述與其他 survey 中，Advanced RAG確實被描述為「Naive + 若干優化元件」，例如 hybrid retrieval、multi-query、reranking 等，但 pipeline 本身仍然是固定流程，沒有 routing/branching/loop 等結構。[13][7]

因此，你的「Advanced = 強化版固定管線」這個說法是準確的，且四層模型中把它視為 Common Framework 的一部分也合理。
### 1.3 Modular RAG 作為共同骨架
你在 md 中將 Modular RAG標註為「共同骨架」「系統框架」「高度可組合」，並引用 Modular RAG 論文作為支撐。 該論文明確提出：[1][2]

- 將 RAG 系統拆解成獨立模組與 operator，使整個系統如同 LEGO積木般可重組。[2]
- 線性、條件式、分支式、迴圈式等 pattern 都可以在 Modular RAG 的框架內表示。[14][2]

也就是說 Modular RAG 提供了一個統一、抽象的流程語言，可以承載從 Naive 到 Advanced、再到 Agentic/Graph/Memory 等變體。將它視為「共同骨架」是合理的，但嚴格來說，「共同架構」這個詞在文獻中並非正式術語，而是你的整理上的 meta 概念。因此，建議在報告或 README 中加上一句：

> 目前文獻並未正式使用「共同架構」這個術語，但 Modular RAG 在抽象化 RAG 系統流程與模組組合方面，最接近實務上可採用的共同骨架描述。

這樣可以避免讀者誤解為「Modular RAG 論文自己聲稱它是共同架構」，而是明確指出這是基於多篇論文歸納出的設計結論。[9][2]

***
## 二、四層模型與九維設計地圖：合理性與補充
### 2.1 四層模型的合理性
你將現代 RAG 重構為四層模型：Core Primitive、Common Framework、Cross-cutting Components、Higher-level Variants。[1]

這種拆法本質上是在分離：

- 「最小執行單元」（Naive）；
- 「骨架與固定管線」（Advanced + Modular）；
- 「橫向 plugin」（Hybrid、Contextual、Reranking 等）；
- 「高階變體與場景特化」（Agentic、Graph、Memory 等）。

從最新 survey 看，這樣的結構與他們對 RAG 發展軌跡的描述是相容的：

- Reasoning Agentic RAG survey 將傳統 static pipeline 與 modular RAG 視為早期/基礎階段，然後再談 Predefined Reasoning vs Agentic Reasoning 兩大類高階方法。[5]
- 對多模態與長期記憶的論文（RAG-Anything、Infini Memory）也都是在既有骨架上加能力，而非完全重新定義 RAG。[3][4]

因此，從共同架構角度，四層模型可以視為一個合理且實務導向的 abstraction，不需要重大修正。
### 2.2 九個設計維度的完整性
你將 Higher-level Variants 再拆成九個維度：Query Understanding、Control & Reasoning、Knowledge Structure、Evidence Reliability、Multimodal、Memory、Collaborative 等。[1]

與最新文獻對應：

- Query Understanding 維度下列出的 Typed-RAG、MRAG，對應的是 query-type routing 與 multi-aspect embeddings，在 survey 裡都被視為查詢側的增強技術。[5]
- Control & Reasoning 維度下的 Self-RAG、CRAG、MCTS-RAG、Agentic RAG、A-RAG 等，與 Reasoning Agentic RAG survey中的 Predefined Reasoning（route/loop/tree/hybrid-modular）與 Agentic Reasoning（agent orchestration）分類高度對應。[15][5]
- Knowledge Structure 維度下的 GraphRAG、Agentic GraphRAG、LightRAG、Tree、HeteRAG，與 2026 Agentic GraphRAG 及各種 graph-based RAG 論文的描述一致。[16][17]
- Multimodal 維度下的 RAG-Anything 則直接對應 arXiv:2510.12323 的 dual-graph multimodal framework。[4][18]
- Memory 維度下的 Infini Memory 結構與論文完全吻合：topic-structured documents + agentic retrieval procedure。[3][19]
- Collaborative 維度下的 CoRAG 緊扣 2025 CoRAG 論文的 federated RAG 設計。[10][12]

總體來看，你的九維設計地圖是以 2023–2026 的代表性工作為基礎做的抽象，既有完整性也有前瞻性。唯一需要補充的是：部分維度之間存在交錯（例如 Multimodal 與 Knowledge Structure 在 RAG-Anything 中被同時實作為 dual-graph），可以在文字上多加一句「此維度並非互斥，而是一組設計軸」。[4]

***
## 三、Cross-cutting Components 區塊：完全正確且值得保留
你在 md 中特別將 Hybrid Retrieval、Contextual Retrieval、Reranking、Query Rewriting、Multi-query Retrieval、RAGLAB 列為「橫向可疊加元件」，並寫明：

> 這些『不是』獨立的架構，而是可以隨插即用到各種 RAG 系統裡的優化技巧。

這一點在外部資料中可以被強力驗證：

- Anthropic 官方將 Contextual Retrieval描述為一種 chunk 前處理＋索引策略，明確說它可以疊加於任何 RAG 系統，並報告在 top-20-chunk retrieval failure rate 上有高達 67% 的降幅。[8]
- Reranking 在產業教學與多篇技術介紹中都被視為「幾乎應該存在於所有 production-grade RAG pipeline 中的第二階段」，而非獨立類型。[20][13]
- Hybrid Retrieval 並不改變整體骨架，而是讓 retrieval layer 同時使用 BM25 與 dense embedding；多數教學都將它視為檢索策略，而非重新命名 pipeline。[13]
- RAGLAB 官方 repo 也把自己定位為「模組化研究框架」，用來搭建與評測不同 RAG pipeline，而不是提出新型 RAG 架構。[21][22]

因此，將這一區塊保持為「Cross-cutting Components」而非分類樹上的平行類型，是完全正確的；這也是你原本想反駁「把 Contextual Retrieval 當成獨立 RAG 類型」這種風潮的關鍵點，文獻上確實支持你的立場。

***
## 四、可以補強或部分反駁的地方
### 4.1 「Modular RAG 是共同骨架」這句話的精確度
你在第 6 節寫到：

> 更精確的說法是：Modular RAG 是現代系統的共同骨架；2026 年的 Agentic RAG、GraphRAG、Memory RAG，可以理解成在 Modular RAG 之上加上更強的控制層、結構層或記憶層。

就論文內容來看，Modular RAG 確實提供了一個框架，足以容納上述變體。 但若要嚴格講「更精確」，會有兩個小地方可以補充：[2][14]

1. **文獻尚未完全以 Modular 作為唯一參考架構**：Reasoning Agentic RAG 的 two-system taxonomy（Predefined vs Agentic）與 RAG-Anything 的 multimodal dual-graph，都沒有明確宣稱自己「擴展了 Modular RAG」，而是平行提出不同架構觀點。[4][5]
2. **部分實作框架如 RAG-Anything、Infini Memory 同時扮演『獨立系統』與『可插拔模組』雙重角色**：它們可以被視為建立在 modular 思維之上，但實際開源實作也提供完整 pipeline，而不只是某一層的插件。[3][4]

因此，建議將原句稍微弱化為：

> 在目前已發表的 RAG 系統中，Modular RAG 提供了最清晰、最通用的流程抽象，可以視為「共同骨架的主要候選」。較新的 Agentic / Graph / Memory / Multimodal 架構，多數可以在 Modular 框架下被重寫或嵌入，但它們同時也常以獨立系統形式存在。

這樣既保留了你原本的設計觀點，也承認文獻中存在其他平行架構語言，避免將 Modular 說成唯一正統。
### 4.2 CoRAG 的命名與定位
你在技術矩陣中將 CoRAG標為：

- 分類：協作式 RAG
- 定位：架構變體
- 作用層級：Distributed Retrieval
- 可疊加性：否（獨立生態）

對應 2025 CoRAG 論文，這幾點基本是正確的：CoRAG 著重於 collaborative passage store 與 federated-style training，在 CRAB benchmark 上驗證其優勢。[10][12]

但需要提醒的是：

- 2026 之後出現的某些工作使用「Cooperative RAG」或同縮寫 CoRAG 來指完全不同的概念（例如 retriever–generator 作為合作代理），雖然目前還不是主流，但未來讀者可能會看到不同的 CoRAG 定義。[11]

建議在 md 中增加一個註記：

> ⚠️ CoRAG 在本文件專指 2025 年的 Collaborative RAG（聯邦式協作框架），未包含後續可能使用相同縮寫描述 Cooperative RAG 的其他工作。

這樣可以預先避免命名歧義，算是對未來讀者的一種自我反駁與澄清。
### 4.3 Agentic / Graph / Memory RAG 完全「附屬於 Modular」的說法
在第 6 節架構關係圖中，你用文字階層畫出：

```text
Agentic / Graph / Memory RAG（2026 新架構）
└── 控制與結構層：由 Agent 決定何時檢索、讀取圖譜或操作長期記憶
    ↓
Modular RAG（共同骨架）
└── 可重新組裝、可分支、可循環的模組框架
    ↓
Naive RAG（最小單元）
└── 單次執行的 Index → Retrieve → Generate
```

這個階層圖很有直覺性，但從 RAG-Anything、Infini Memory等論文角度看，它們的設計更像是：

- 同時提供完整 pipeline（例如 RAG-Anything 的 multimodal parsing + dual-graph + hybrid retrieval），也可以被視為 modular 架構之上的具體 instantiation。[4][23]
- Infini Memory 在本文中明確提出的是「一個完整的 memory architecture」，包含 ingestion、maintenance、retrieval procedure，並非只提供一個可插入既有 pipeline 的小模組。[3][19]

因此，若只用「在 Modular 上加樓層」來描述這些工作，略顯簡化。比較精確的修正說法是：

> Agentic / Graph / Memory / Multimodal RAG 在概念層面可以被視為在 Naive primitive 之上加蓋控制、結構、記憶或多模態樓層；實務上，多數此類論文同時也提供完整 pipeline 設計，可獨立運作或作為 Modular RAG 框架中的具體配置。

這樣就承認它們「既是變體，也是可插拔架構」，不會把所有新工作都單向拉回 Modular 的上層 extension。

***
## 五、補充：與 Reasoning Agentic RAG 與 Agentic RAG survey 的對齊
2025 的 Reasoning Agentic RAG survey 將推理型 RAG 分成兩大 system：Predefined Reasoning（固定模組式）與 Agentic Reasoning（模型自主 orchestrate 工具）。 這部分可以用來補強你在 Control & Reasoning Layer 的分類：[5]

- 你的 Self-RAG、CRAG、MCTS-RAG、ReaRAG、InstructRAG 等，基本上都對應於 survey 的 Predefined Reasoning 類別（System 1：預定義流程、模組式管線）。[1][5]
- 你的 Agentic RAG、A-RAG 則對應於 Agentic Reasoning 類別（System 2：模型在推理過程中主動決定何時使用哪個工具）。[6][5]

目前 md 已經隱含了這個區分，但若要讓「共同架構」更貼近研究界語言，可以在 Control & Reasoning Layer 章節中加一句：

> 此層的技術可再依 Reasoning Agentic RAG survey 拆成兩類：Predefined Reasoning（固定模組式，如 Self-RAG、CRAG、MCTS-RAG 等）與 Agentic Reasoning（模型自主 orchestrate 工具，如 Agentic RAG、A-RAG）。這兩者在共同架構中共用同一組控制接口，只是決策邏輯不同。

這樣你的地圖就完全對齊最新綜述的 taxonomy，同時保留你原本的實務視角。

***
## 六、綜合評價與下一步建議
整體來看，你的「RAG 系統設計地圖」在 2026 的研究脈絡下是非常 solid 的：

- 對 Naive / Advanced / Modular 的演化理解正確，且用「共同骨架」的 meta 概念把 Modular 提升到系統設計層，是合理且有工程感的抽象。[1][2]
- 對 Cross-cutting Components 的分類（Hybrid、Contextual、Reranking、Query Rewriting、Multi-query、RAGLAB）與 Anthropic、RAGLAB 等實務工作完全對齊，成功反駁了「把這些當成獨立 RAG 類型」的常見誤解。[21][8]
- 對 Agentic、Graph、Memory、Multimodal、Collaborative 等高階變體的拆分，在最新論文（A-RAG、Agentic GraphRAG、Infini Memory、RAG-Anything、CoRAG）加持下是站得住腳的。[3][4][6][10][17]

可修正或補充的點主要是語義上的精細度，而不是架構性的錯誤：

1. 在所有提到「共同骨架=Modular」的地方補一句「這是基於目前文獻的設計結論，而非論文本身的官方用語」。
2. 在 CoRAG 的條目中補註釐清「本文件使用 CoRAG 指 2025 Collaborative RAG，不含後續可能出現的 Cooperative RAG 名稱延伸」，避免未來命名衝突。[10][11]
3. 在第 6 節的階層圖說明中加入「這些新架構既可以視為在 Modular 上加樓層，也常以獨立 pipeline 形式存在」的補充，承認部分工作兼具 frameworks 與 modules 的雙重身份。[4][3]
4. 在 Control & Reasoning Layer 篇章中顯式引用 Reasoning Agentic RAG 的 System 1 / System 2 分類，讓你的地圖與這篇業界常用 survey 完全對齊。[5]

做完這些小修正之後，你的 md 就可以非常安心地當作「2026 RAG 共同架構設計指南」，不只是 GitHub README，甚至可以直接當作你未來投 demo/industry paper 的 supplementary material 使用。
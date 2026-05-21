Feature: 檢視 RAG System Map
  使用者可以開啟互動式 GUI，探索 ai_system_map.json 中的 RAG component node、connection edge、evidence、slot status 與 risk hints。

  Rule: 使用者可以用 viewer command 載入 map JSON

    Example: 開啟 RAG System Map viewer
      Given 使用者有 map JSON "outputs/ai_system_map.json"
      When 使用者執行 viewer command "kai-mind viewer outputs/ai_system_map.json"
      Then GUI 載入狀態為
        | map_json                    | loaded |
        | outputs/ai_system_map.json | true   |

    Example: map JSON 不存在或格式無效時顯示錯誤狀態
      Given 使用者沒有可載入的 map JSON "outputs/broken-map.json"
      When 使用者執行 viewer command "kai-mind viewer outputs/broken-map.json"
      Then GUI 載入狀態為
        | map_json                | loaded | error_visible |
        | outputs/broken-map.json | false  | true          |
      And GUI error state 包含
        | field        |
        | map_json     |
        | error_reason |
      And GUI graph 狀態為
        | graph_visible |
        | false         |

  Rule: GUI 必須以 node / edge graph 顯示 RAG 系統

    Example: 顯示 indexing flow 與 query_answer flow
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者檢視 RAG System Map
      Then GUI flows 顯示狀態為
        | flow         | visible |
        | indexing     | true    |
        | query_answer | true    |

  Rule: GUI 必須用不同視覺樣式區分指定 component 類型

    Example: component 類型具備視覺樣式
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者檢視 RAG System Map
      Then GUI component visual types 包含
        | component_type    |
        | data source       |
        | parser            |
        | chunking          |
        | embedding         |
        | vector store      |
        | retriever         |
        | LLM               |
        | citation          |
        | external endpoint |
        | network exposure  |

  Rule: 使用者點選 node 時可以查看 evidence 與 slot status

    Example: 點選 Qdrant node
      Given GUI 已載入含有 Qdrant node 的 "outputs/ai_system_map.json"
      When 使用者點選 node "qdrant_vector_db"
      Then detail panel 顯示 node 資料
        | field  | value        |
        | slot   | vector_store |
        | status | detected     |
        | name   | Qdrant       |
      And detail panel 顯示 evidence
        | kind           | file               | path                  |
        | docker_service | docker-compose.yml | services.qdrant.image |

  Rule: 使用者點選 edge 時可以查看 connection reason

    Example: 點選 retriever 到 vector_store 的 edge
      Given GUI 已載入含有 query_answer edge 的 "outputs/ai_system_map.json"
      When 使用者點選 edge "retriever->vector_store"
      Then detail panel 顯示 edge 資料
        | from_slot | to_slot      | relationship         |
        | retriever | vector_store | queries_vector_store |

  Rule: GUI 必須支援指定 filter 類型

    Example: 顯示 Epic 1 filter 清單
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者開啟 filter controls
      Then filter controls 包含
        | filter_type      |
        | RAG slot         |
        | detected         |
        | missing          |
        | external endpoint |
        | network exposure |
        | risk hint        |

    Example: 套用 filter 時保留完整 graph 並高亮符合項目
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者套用 filter "risk hint"
      Then GUI filter 顯示狀態為
        | full_graph_visible | matched_items_highlighted | unmatched_items_hidden |
        | true               | true                      | false                  |

  Rule: GUI 必須支援基本 zoom、pan、drag

    Example: graph interaction controls
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者檢視 graph interaction controls
      Then graph interaction controls 包含
        | control |
        | zoom    |
        | pan     |
        | drag    |

  Rule: GUI 不得直接顯示完整 API key 或 secret value

    Example: secret-like value 只能前後少量顯示於 GUI
      Given GUI 已載入包含 secret-like value evidence 的 "outputs/ai_system_map.json"
      When 使用者查看 detail panel
      Then GUI secret display 狀態為
        | full_secret_visible | prefix_suffix_visible | middle_masked |
        | false               | true                  | true          |

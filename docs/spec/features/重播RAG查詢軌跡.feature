Feature: 重播 RAG 查詢軌跡
  使用者可以在 GUI 輸入測試問題，KAI-Mind 收集一次 query trace，並把 trace events 映射回 RAG System Map。

  Rule: 使用者可以在 GUI 輸入測試問題觸發 query trace

    Example: 送出測試問題
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者在 GUI 輸入測試問題
      Then query trace 狀態為
        | state     |
        | requested |

  Rule: KAI-Mind 必須找到 RAG app / API endpoint 才能送出 query

    Example: 找到 RAG app / API endpoint
      Given RAG System Map 包含 app_api_or_orchestrator endpoint
      When 使用者在 GUI 輸入測試問題
      Then query trace endpoint 狀態為
        | endpoint_found |
        | true           |

    Example: 找不到 RAG app / API endpoint 時顯示 endpoint_not_found
      Given RAG System Map 不包含 app_api_or_orchestrator endpoint
      When 使用者在 GUI 輸入測試問題
      Then 操作失敗
      And query trace endpoint 狀態為
        | endpoint_found | error                | query_sent |
        | false          | endpoint_not_found   | false      |

  Rule: Query trace 可以透過 proxy wrapper、trace hook 或 sample trace 收集

    Example: Epic 1 MVP 會呼叫 detected RAG endpoint 並收集 basic trace
      Given GUI 已載入 "outputs/ai_system_map.json"
      When 使用者在 GUI 輸入測試問題
      Then trace collection MVP 狀態為
        | calls_detected_endpoint | collects_basic_trace |
        | true                    | true                 |
      And trace collection advanced sources 包含
        | source        | scope    |
        | proxy wrapper | advanced |
        | trace hook    | advanced |

  Rule: Query trace events 必須映射回 RAG System Map 的 slots、nodes 或 edges

    Example: trace events mapped to RAG steps
      Given query trace 已收集 events
      When GUI 顯示 query trace replay
      Then trace replay steps 包含
        | step                          |
        | user query                    |
        | query processing              |
        | retriever                     |
        | vector store                  |
        | retrieved chunks              |
        | prompt builder                |
        | LLM                           |
        | citation / response composer  |
        | final response                |

  Rule: Replay 必須支援播放控制

    Example: replay controls
      Given query trace events 已映射回 RAG System Map
      When GUI 顯示 query trace replay
      Then replay controls 包含
        | control       |
        | pause         |
        | step forward  |
        | step backward |
        | replay        |

  Rule: 目前 trace step 對應的 component 與 edge 必須高亮

    Example: replay step highlight
      Given query trace replay 正在顯示 retriever step
      When GUI 顯示目前 trace step
      Then highlighted map elements 包含
        | element_type | element    |
        | component    | retriever  |

    Example: trace step 發生 error 或 timeout 時保留 partial replay
      Given query trace replay 包含 error step
      When GUI 顯示目前 trace step
      Then trace replay 狀態為
        | partial_replay_visible | error_step_highlighted | replay_discarded |
        | true                   | true                   | false            |
      And detail panel 顯示 trace step error
        | field | visible |
        | error | true    |

  Rule: Detail panel 必須顯示 trace step 資料

    Example: trace step detail panel fields
      Given query trace replay 正在顯示目前 step
      When 使用者查看 detail panel
      Then detail panel trace fields 包含
        | field            |
        | sequence_index   |
        | timestamp        |
        | input            |
        | output           |
        | latency          |
        | error            |
        | retrieved chunks |

  Rule: 完整 runtime trace capture 可作為 Epic 1 進階交付或後續銜接

    Example: runtime trace capture scope
      Given Epic 1 MVP 已呼叫 detected RAG endpoint 並收集 basic trace
      When 使用者檢視 query trace / replay scope
      Then runtime trace capture scope 為
        | capability             | scope    |
        | basic endpoint trace   | mvp      |
        | proxy wrapper capture  | advanced |
        | trace hook capture     | advanced |

Feature: 建立 RAG System Map
  使用者輸入一個既有的 RAG project folder 後，KAI-Mind 產生標準化、可追溯 evidence 的 RAG System Map。

  Rule: 使用者可以用 map command 輸入 project folder

    Example: 對 example project 執行 map command
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then 輸出檔案包含
        | path                        |
        | outputs/ai_system_map.json |
        | outputs/ai_system_map.md   |

    Example: project folder 不存在或不可讀時產生錯誤報告
      Given 使用者沒有可讀取的 project folder "./missing-project"
      When 使用者執行 map command "kai-mind map ./missing-project"
      Then 操作失敗
      And 輸出檔案包含
        | path                     |
        | outputs/map-error.md     |
      And 輸出檔案不包含
        | path                        |
        | outputs/ai_system_map.json |
        | outputs/ai_system_map.md   |
      And 錯誤報告內容包含
        | field          |
        | project_path   |
        | failure_reason |
        | scan_stage     |

    Example: outputs 已存在時產生 timestamped output directory
      Given 使用者有 project folder "./example-project"
      And output directory "outputs/" 已包含既有檔案
      When 使用者執行 map command "kai-mind map ./example-project"
      Then 輸出檔案包含
        | path                                           |
        | outputs/2026-05-19T000000/ai_system_map.json  |
        | outputs/2026-05-19T000000/ai_system_map.md    |
      And 既有輸出檔案保留狀態為
        | overwritten |
        | false       |

  Rule: Epic 1 的 classification 固定為 RAG 並保留未來 classification layer 欄位

    Example: RAG classification placeholder
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then RAG System Map classification 為
        | field             | value                         |
        | system_type       | rag                           |
        | mode              | user_selected_or_default      |
        | selected_template | rag-core-v1                   |
        | future_layer      | architecture_classification   |

  Rule: System Map 必須載入 RAG reference architecture component slots

    Example: 載入 rag-core-v1 component slots
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then RAG reference architecture component slots 包含
        | slot                          |
        | data_sources                  |
        | document_loader               |
        | chunking                      |
        | embedding_model               |
        | vector_store                  |
        | app_api_or_orchestrator       |
        | query_processing              |
        | retriever                     |
        | prompt_builder                |
        | llm                           |
        | citation_or_response_composer |
        | guardrails                    |
        | observability                 |

  Rule: Scanner 必須根據明確檔案與設定訊號掃描 project folder

    Example: Epic 1 初始掃描檔案類型
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then scanner 檔案掃描範圍包含
        | file_pattern       |
        | .env               |
        | .env.example       |
        | docker-compose.yml |
        | Dockerfile         |
        | requirements.txt   |
        | pyproject.toml     |
        | package.json       |
        | config.yaml        |
        | config.yml         |
        | *.json config      |
        | README.md          |

    Example: config 或 docker-compose 解析失敗時產生 partial System Map
      Given project folder 包含無法解析的 config file "docker-compose.yml"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then 輸出檔案包含
        | path                        |
        | outputs/ai_system_map.json |
        | outputs/ai_system_map.md   |
      And scanner parse errors 包含
        | file               | error_recorded_as |
        | docker-compose.yml | evidence          |
      And risk hints 包含
        | type        | target             | target_type    | evidence_id                  | rule_id            | rationale                                  | uncertainty                               |
        | parse_error | docker-compose.yml | component_slot | evidence_docker_parse_error  | config_parse_error | scanner could not parse docker-compose.yml | partial map may miss docker-based signals |

  Rule: Component slot status 只能使用明確允許值

    Example: RAG slot status values
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then component slot status 允許值為
        | status         |
        | detected       |
        | missing        |
        | not_configured |
        | not_applicable |

  Rule: Detected component 必須包含 slot、status、name、evidence

    Example: 偵測到 Qdrant vector store
      Given project folder 包含 docker-compose.yml
      When 使用者執行 map command "kai-mind map ./example-project"
      Then detected component 包含
        | slot         | status   | name   |
        | vector_store | detected | Qdrant |
      And detected component evidence 包含
        | kind           | file               | path                   | value         |
        | docker_service | docker-compose.yml | services.qdrant.image  | qdrant/qdrant |
        | published_port | docker-compose.yml | services.qdrant.ports  | 6333:6333     |

    Example: evidence file 使用 project-relative POSIX path
      Given project folder 包含 source file "src/rag.py"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then evidence file path 格式為
        | file       | path_format             |
        | src/rag.py | project_relative_posix  |

  Rule: 沒有掃到 evidence 的 slot 不得假裝 detected

    Example: citation slot 沒有 evidence 時標示 missing
      Given project folder 沒有 citation_or_response_composer evidence
      When 使用者執行 map command "kai-mind map ./example-project"
      Then component slot 狀態包含
        | slot                          | status  |
        | citation_or_response_composer | missing |
      And component slot instances 數量為
        | slot                          | instances_count |
        | citation_or_response_composer | 0               |

  Rule: System Map 不得使用 confidence 表示推測程度

    Example: RAG System Map 使用 evidence 與 status
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then RAG System Map 欄位存在狀態為
        | field                    | exists |
        | components_by_slot.status | true   |
        | evidence                 | true   |
        | confidence               | false  |

  Rule: Scanner 必須輸出初步 network exposure risk hints

    Example: Qdrant published port 產生 network exposure hint
      Given project folder 的 docker-compose.yml 包含 services.qdrant.ports "6333:6333"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then risk hints 包含
        | type             | target           | target_type        | evidence_id             | rule_id                       | rationale                                        | uncertainty                             | severity_hint |
        | network_exposure | qdrant_vector_db | component_instance | evidence_qdrant_ports   | docker_published_port_exposure | published port can expose Qdrant outside localhost | Epic 1 does not run full port security check | high          |

  Rule: JSON output 必須包含 Epic 1 指定內容

    Example: ai_system_map.json content contract
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then ai_system_map.json content fields 包含
        | field                       |
        | project metadata            |
        | system type classification placeholder |
        | reference architecture ID   |
        | RAG component slots         |
        | slot status                 |
        | detected component instances |
        | indexing flow               |
        | query / answer flow         |
        | endpoints                   |
        | config evidence             |
        | risk hints                  |
        | recommended next checks     |

  Rule: Markdown summary 必須包含 Epic 1 指定章節

    Example: ai_system_map.md summary sections
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then ai_system_map.md sections 包含
        | section                         |
        | 系統總覽                        |
        | RAG component slot coverage      |
        | 偵測到的元件與 missing slots      |
        | indexing flow                   |
        | query / answer flow             |
        | 可能的外部 endpoint             |
        | 可能的 network exposure          |
        | 後續建議檢查項目                |

  Rule: RAG System Map 必須輸出 recommended next checks

    Example: recommended next checks
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then recommended next checks 包含
        | check_name          |
        | runtime_readiness   |
        | privacy_exposure    |
        | rag_knowledge_trust |

  Rule: Scanner 不得直接顯示完整 API key 或 secret value

    Example: secret-like value 只能前後少量顯示
      Given project folder 包含 secret-like value
      When 使用者執行 map command "kai-mind map ./example-project"
      Then scanner secret display 狀態為
        | full_secret_visible | prefix_suffix_visible | middle_masked |
        | false               | true                  | true          |

  Rule: AI 不得成為 scanner evidence 的 source of truth

    Example: AI 只可輔助呈現，不可創造 component
      Given 使用者有 project folder "./example-project"
      When 使用者執行 map command "kai-mind map ./example-project"
      Then scanner evidence source of truth 狀態為
        | stage                              | ai_is_source_of_truth |
        | 掃描 repo / config / Docker        | false                 |
        | 判斷 RAG component slot status     | false                 |
        | 建立 ai_system_map.json           | false                 |
        | Graph layout / label 優化          | false                 |
        | Markdown summary                   | false                 |
        | GUI detail explanation             | false                 |
        | Query trace replay                 | false                 |

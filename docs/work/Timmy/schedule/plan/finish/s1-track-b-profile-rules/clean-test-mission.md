# 前提
請先閱讀並遵守 `/Users/linjunting/Systograph/AGENTS.md`。只有在專案結構真的改變、且需要成為長期開發規則時，才更新 AGENTS.md；一般實作紀錄請寫到 TODO / Report。

# 背景知識
1.目前專案的計劃要做的事情如下： 
`/Users/linjunting/Systograph/docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md`

2.目前專案後端程式碼如下：
`/Users/linjunting/Systograph/src`
3.目前的專案前端程式碼如下：
`/Users/linjunting/Systograph/frontend`
4.目前過去已經完成的計劃：`/Users/linjunting/Systograph/docs/work/Timmy/schedule/plan/finish` 這裡面有之前完成的計劃內容，可以參考裡面的內容來了解之前的開發過程以及目前專案的狀態
5.目前專案的大方向設計文件如下：`/Users/linjunting/Systograph/docs/work/Timmy/design`
6.目前的專案結構下：`/Users/linjunting/Systograph/AGENTS.md`
7.這是專案目前的spec:` /Users/linjunting/Systograph/docs/spec`
8.這是預計的JSON 相關資訊（還可以修改）:`/Users/linjunting/Systograph/docs/work/Timmy/design/EPIC1/frontend-json-handoff`
9.這是我們的API 相關資訊:`/Users/linjunting/Systograph/docs/API-GUIDE.md`
10.這是我們的MODEL CONTRACT: `/Users/linjunting/Systograph/docs/MODEL-CONTRACT.md`
11.過程中你可以使用 "context7" MCP（如果要查詢的資料適合用context7查詢的話）來查找最新資訊或是直接上網查詢相關資訊
12.我們專案目前會介接的開源專案(根據需要，會修改其中某些流程或是直接接到我的系統裡面)如下：`/Users/linjunting/Systograph/ref-opensource`

# 任務
1.現在我的測試我覺得非常的亂 請開始幫我整理 你可以參考 `/Users/linjunting/R2R/py/tests`寫測試的方式或是參考現有github 開源相關專案寫測試的方式來幫我整理
2.幫我補齊Unit Test和Integration Test，如果我的測試程式碼沒有寫完整，你也可以自己補測試程式再測試。確保所有測試都有補齊，補完後確保所有測試都通過。

2.使用 linux torvald `/Users/linjunting/Systograph/.cursor/rules/linus_torvalds.mdc` 的思考方式，你必須使用適合的skills和mcp工具去協助你完成任務，你必須使用 "context7" MCP來查找相關最佳實踐資料
請注意！改善完後要能夠通過所有測試，如果我的測試程式沒有寫完整，你也可以自己補測試程式再測試

# 定期紀錄TODO
先規劃分成幾個階段做事，把每個階段要做的事情放在 `/Users/linjunting/Systograph/docs/work/Timmy/schedule/todo`，檔案名稱使用 “今天日期-階段名稱-TODO”
這個todo 必須要清楚易懂，讓其他人可以根據這個todo 了解你做了什麼事情，這個todo你必須清楚記錄你的“實作邏輯”、“步驟”，這些區塊要區分清楚讓人一目瞭然容易閱讀！   

# 定期紀錄Report
每個階段完成後，你必須要把你做了什麼事情記錄在 `/Users/linjunting/Systograph/docs/work/Timmy/schedule/report`，檔案名稱使用 “今天日期-完成的階段名稱-REP”
這個report 必須要清楚易懂，讓其他人可以根據這個report 了解你做了什麼事情，這個report你必須清楚記錄你的“實作邏輯”、“步驟”、“測試方式”，“還有你遇到的問題以及你是怎麼解決的”，“最後還有測試結果如何”，這些區塊要區分清楚讓人一目瞭然容易閱讀簡單易懂！


# 測試相關注意事項 


如果執行測試完有錯誤，你必須去看相關log，如果這是跟這次改動相關的測試錯誤請你修正它們，直到所有相關測試都通過為止！，如果不是這次改動相關的測試錯誤，你必須記錄下來並且告訴我！
但是要記得，
1.你修改完後不能影響到其他功能，你必須以全面性觀點去看問題，不要改了一個問題跑出另一個問題！
2.遇到不會的或是不確定的問題，你必須使用 "context7" MCP來查找相關軟體工程最佳實踐資料

# 約束
1. 你必須通過所有測試程式碼
2. 你修改完後不能影響到其他功能，你必須以全面性觀點去看問題，不要改了一個問題跑出另一個問題！
3. 遇到不會的或是不確定的問題，你必須使用 "context7" MCP（如果要查詢的資料適合用context7查詢的話）來查找最新資訊或是直接上網查找相關軟體工程最佳實踐資料

## 注意事項
請注意，你必須獨立完成此工作，過程中所有的決策都不必徵求任何我的同意，直接照你自己的意思任何該改啥
就直接下去改！！我相信你！！ 因為我人會出門一趟，不會在座位上，我完全信任你獨立工作的能力，因此，你
必須一直工作直到確認底下條件全部驗收通過，才能停止！！ 

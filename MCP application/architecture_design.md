# 即時國際經濟資訊系統 - 模型階段初步架構設計與技術選型

## 專案目標 (模型階段)

在低成本的前提下，建構一個即時國際經濟資訊系統的基礎模型，驗證核心功能的可行性，並初步評估市場需求。系統應能監控選定的免費/低成本資訊來源，識別關鍵的經濟或地緣政治事件，並產生即時通知（初步通過簡單方式）。

## 初步系統架構設想

考慮到模型階段的需求和資源限制，系統將採用相對簡單的架構，包含以下核心組件：

1.  **數據採集腳本/服務 (Data Collection Script/Service):**
    *   職責：負責從選定的免費或低成本線上來源（如特定政府網站、公開的經濟數據接口、部分新聞網站的公開 feed）自動抓取即時或近即時的國際經濟和地緣政治相關資訊。
    *   技術實現：使用 Python 編寫，利用現有的網路爬蟲庫 (如 `requests`, `BeautifulSoup`, `Scrapy`) 或處理 API 調用的庫。

2.  **資訊處理腳本/服務 (Information Processing Script/Service):**
    *   職責：接收採集的原始數據，進行清洗、結構化、關鍵詞提取和簡單的事件識別。
    *   技術實現：使用 Python 編寫。可能包含基於規則或簡單模式匹配的邏輯來識別特定事件（如日期匹配、關鍵詞組合）。

3.  **數據庫 (Database):**
    *   職責：存儲採集到的原始數據、處理後的結構化信息以及識別到的事件記錄。
    *   技術選型：初步使用 **SQLite**。這是一個輕量級的、基於文件的數據庫，易於設置和管理，適合模型階段的數據存儲需求。未來擴展可考慮 PostgreSQL 等服務器數據庫。

4.  **消息傳輸/佇列 (Message Queue - Simple):**
    *   職責：在數據採集、資訊處理和通知發送模組之間傳遞信息，實現一定程度的解耦。
    *   技術選型：模型階段可以使用簡單的**內存佇列**、基於數據庫的簡單實現或文件作為臨時存儲。

5.  **通知發送腳本/服務 (Notification Sending Script/Service):**
    *   職責：從數據庫或消息佇列獲取識別到的事件信息，並通過簡單方式發送通知。
    *   技術實現：使用 Python 編寫。初步通知方式可以是在控制台打印、寫入日誌文件，或者集成簡單的免費郵件/消息發送服務（需研究可行性）。

6.  **（可選）簡單的使用者介面 (Simple User Interface):**
    *   職責：提供一個基本的方式來展示接收到的資訊和通知。
    *   技術實現：模型階段可以是一個簡單的命令行介面，或者使用 Python 的輕量級 Web 框架 (如 Flask) 搭建一個基本的網頁來展示數據和通知列表。

## 技術選型總結

*   **主要開發語言：** Python
*   **數據庫：** SQLite
*   **消息傳輸：** 簡單內存佇列/文件/數據庫實現
*   **數據採集：** Python 相關庫 (requests, BeautifulSoup, Scrapy 等)
*   **資訊處理：** Python 編寫的規則或模式匹配邏輯
*   **通知發送：** Python 編寫，初步輸出到控制台/文件/簡單第三方服務
*   **使用者介面 (可選)：** 命令行或基於 Flask 的簡單網頁

這個技術棧主要依賴於開源和免費工具，符合模型階段的低成本目標。未來隨著專案的發展和需求的明確，再逐步引入更強大和可擴展的技術。 
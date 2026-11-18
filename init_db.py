import sqlite3

def init_database():
    conn = sqlite3.connect('medical_room.db')
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS medical_supplies')
    cursor.execute('DROP TABLE IF EXISTS voice_query_logs')

    # 1. 建立耗材與器械主檔表 (精簡為直接對應 A1~A5 櫃)
    cursor.execute('''
        CREATE TABLE medical_supplies (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            aliases TEXT NOT NULL,
            cabinet_id TEXT NOT NULL,
            stock_qty INTEGER NOT NULL,
            min_stock INTEGER NOT NULL
        )
    ''')

    # 2. 建立語音查詢與領用日誌表
    cursor.execute('''
        CREATE TABLE voice_query_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
            raw_audio_text TEXT NOT NULL,
            matched_item TEXT,
            action_type TEXT DEFAULT 'QUERY',
            status TEXT NOT NULL
        )
    ''')

    # 3. 寫入 A1櫃 ~ A5櫃 的醫療器械與耗材
    supplies_data = [
        # A1櫃：注射針筒類
        ("50ml 針筒", "50ml針筒,50cc針筒,大針筒,灌食針筒", "A1櫃", 15, 5),
        ("10ml 針筒", "10ml針筒,10cc針筒,一般針筒", "A1櫃", 30, 10),
        ("3ml 針筒", "3ml針筒,3cc針筒,小針筒,皮下針筒", "A1櫃", 45, 15),

        # A2櫃：採血與靜脈留置類
        ("20G 靜脈留置針", "20g留置針,留置針,軟針,ic針,靜脈針", "A2櫃", 22, 8),
        ("真空採血管 (紫頭)", "紫頭管,採血管,抽血管,紫頭採血管", "A2櫃", 40, 15),
        ("止血帶", "止血帶,壓脈帶,綁帶", "A2櫃", 18, 5),

        # A3櫃：無菌紗布與敷料護理類
        ("4x4 無菌紗布", "無菌紗布,紗布,4x4紗布,大紗布", "A3櫃", 4, 5),
        ("2x2 無菌紗布", "小紗布,2x2紗布", "A3櫃", 28, 10),
        ("優碘消毒棉片", "優碘棉片,優碘,消毒棉片", "A3櫃", 50, 20),
        ("75% 酒精棉片", "酒精棉片,酒精片,酒棉", "A3櫃", 60, 25),
        ("3M 透氣紙膠", "紙膠,透氣膠帶,3m膠帶,醫療膠帶", "A3櫃", 12, 5),
        ("無菌外科手套 (7.0號)", "無菌手套,手術手套,7號手套,手套", "A3櫃", 16, 6),

        # A4櫃：縫合器械與點滴輸液類
        ("無菌縫合器械包", "縫合包,縫合器械,拆線包,器械包", "A4櫃", 8, 3),
        ("3-0 尼龍縫線", "縫線,尼龍線,3-0縫線,不可吸收線", "A4櫃", 14, 5),
        ("15號 無菌手術刀片", "手術刀片,刀片,15號刀片", "A4櫃", 20, 6),
        ("500ml 生理食鹽水", "生理食鹽水,食鹽水,ns,沖洗食鹽水", "A4櫃", 10, 4),
        ("無菌點滴輸液套", "點滴套,輸液套,點滴管,iv套", "A4櫃", 15, 5),

        # A5櫃：緊急處置專櫃 (高風險紅框警示)
        ("腎上腺素 (Epinephrine)", "腎上腺素,急救針,過敏休克針,epinephrine", "A5櫃", 5, 3),
        ("急救甦醒球 (Ambu Bag)", "甦醒球,呼吸球,急救球,ambu", "A5櫃", 3, 2)
    ]

    cursor.executemany('''
        INSERT INTO medical_supplies (item_name, aliases, cabinet_id, stock_qty, min_stock)
        VALUES (?, ?, ?, ?, ?)
    ''', supplies_data)

    conn.commit()
    conn.close()
    print("✅ 資料庫 medical_room.db 初始化完成！(已設定 A1櫃 ~ A5櫃)")

if __name__ == '__main__':
    init_database()
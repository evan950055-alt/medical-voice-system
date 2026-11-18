import sqlite3
import re

DB_PATH = 'medical_room.db'

def extract_quantity(text):
    cn_num_map = {'一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5}
    match = re.search(r'(\d+)\s*(個|包|支|瓶|片|捲|組|副|條)', text)
    if match:
        return int(match.group(1))
    cn_match = re.search(r'([一二兩三四五])\s*(個|包|支|瓶|片|捲|組|副|條)', text)
    if cn_match:
        return cn_num_map[cn_match.group(1)]
    return 1

def search_supply_by_text(raw_text, auto_deduct=True):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    clean_input = raw_text.replace(" ", "").lower()
    requested_qty = extract_quantity(clean_input)

    cursor.execute('''
        SELECT item_id, item_name, aliases, cabinet_id, stock_qty, min_stock 
        FROM medical_supplies
    ''')
    all_items = cursor.fetchall()

    matched_record = None
    for row in all_items:
        item_id, item_name, aliases_str, cabinet, stock, min_stock = row
        alias_list = [a.replace(" ", "").lower() for a in aliases_str.split(',')]
        alias_list.append(item_name.replace(" ", "").lower())

        for alias in alias_list:
            if alias and alias in clean_input:
                matched_record = {
                    "item_id": item_id,
                    "item_name": item_name,
                    "cabinet_id": cabinet,
                    "stock_qty": stock,
                    "min_stock": min_stock,
                    "requested_qty": requested_qty
                }
                break
        if matched_record:
            break

    if matched_record:
        action_type = "QUERY_ONLY"
        if auto_deduct and matched_record["stock_qty"] > 0:
            new_qty = max(0, matched_record["stock_qty"] - requested_qty)
            cursor.execute('UPDATE medical_supplies SET stock_qty = ? WHERE item_id = ?', (new_qty, matched_record["item_id"]))
            matched_record["stock_qty"] = new_qty
            action_type = f"AUTO_DEDUCT (-{requested_qty})"

        matched_record["is_low_stock"] = matched_record["stock_qty"] < matched_record["min_stock"]

        cursor.execute('''
            INSERT INTO voice_query_logs (raw_audio_text, matched_item, action_type, status)
            VALUES (?, ?, ?, ?)
        ''', (raw_text, matched_record["item_name"], action_type, "SUCCESS"))
        conn.commit()
        conn.close()
        return {"found": True, "data": matched_record}
    else:
        cursor.execute('''
            INSERT INTO voice_query_logs (raw_audio_text, matched_item, action_type, status)
            VALUES (?, ?, ?, ?)
        ''', (raw_text, "無匹配品項", "NONE", "NOT_FOUND"))
        conn.commit()
        conn.close()
        return {"found": False, "raw_text": raw_text}

def deduct_supply_stock(item_id, item_name, qty=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT stock_qty, min_stock, cabinet_id 
        FROM medical_supplies WHERE item_id = ?
    ''', (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    current_stock, min_stock, cabinet = row
    new_stock = max(0, current_stock - qty)

    cursor.execute('UPDATE medical_supplies SET stock_qty = ? WHERE item_id = ?', (new_stock, item_id))
    cursor.execute('''
        INSERT INTO voice_query_logs (raw_audio_text, matched_item, action_type, status)
        VALUES (?, ?, ?, ?)
    ''', (f"[手動補扣] {item_name}", item_name, f"MANUAL_DEDUCT (-{qty})", "SUCCESS"))

    conn.commit()
    conn.close()

    return {
        "item_id": item_id,
        "item_name": item_name,
        "cabinet_id": cabinet,
        "stock_qty": new_stock,
        "min_stock": min_stock,
        "requested_qty": qty,
        "is_low_stock": new_stock < min_stock
    }

def get_all_supplies():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT item_id, item_name, aliases, cabinet_id, stock_qty, min_stock
        FROM medical_supplies
        ORDER BY cabinet_id, item_id
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def restock_single_item(item_id, item_name, add_qty):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE medical_supplies SET stock_qty = stock_qty + ? WHERE item_id = ?', (add_qty, item_id))
    cursor.execute('''
        INSERT INTO voice_query_logs (raw_audio_text, matched_item, action_type, status)
        VALUES (?, ?, ?, ?)
    ''', (f"[後台補貨] {item_name}", item_name, f"RESTOCK (+{add_qty})", "SUCCESS"))
    conn.commit()
    conn.close()

def restock_all_low_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE medical_supplies SET stock_qty = min_stock * 2 WHERE stock_qty < min_stock')
    updated_count = cursor.rowcount
    if updated_count > 0:
        cursor.execute('''
            INSERT INTO voice_query_logs (raw_audio_text, matched_item, action_type, status)
            VALUES (?, ?, ?, ?)
        ''', (f"[一鍵補貨] 共補齊 {updated_count} 項低庫存耗材", "多項低庫存耗材", "BATCH_RESTOCK", "SUCCESS"))
    conn.commit()
    conn.close()
    return updated_count

def add_new_supply_item(item_name, aliases, cabinet_id, stock_qty, min_stock):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO medical_supplies (item_name, aliases, cabinet_id, stock_qty, min_stock)
        VALUES (?, ?, ?, ?, ?)
    ''', (item_name, aliases, cabinet_id, stock_qty, min_stock))
    cursor.execute('''
        INSERT INTO voice_query_logs (raw_audio_text, matched_item, action_type, status)
        VALUES (?, ?, ?, ?)
    ''', (f"[新增耗材] {item_name}", item_name, f"NEW_ITEM (+{stock_qty})", "SUCCESS"))
    conn.commit()
    conn.close()

def get_recent_logs(limit=6):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, raw_audio_text, matched_item, action_type, status
        FROM voice_query_logs
        ORDER BY log_id DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows
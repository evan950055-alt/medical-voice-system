import os
import streamlit as st
import pandas as pd
from init_db import init_database
from voice_engine import (
    search_supply_by_text, deduct_supply_stock, get_recent_logs,
    get_all_supplies, restock_single_item, restock_all_low_items, add_new_supply_item
)

# 雲端啟動時若尚未建立資料庫，自動執行初始化
if not os.path.exists("medical_room.db"):
    init_database()
from voice_engine import (
    search_supply_by_text, deduct_supply_stock, get_recent_logs,
    get_all_supplies, restock_single_item, restock_all_low_items, add_new_supply_item
)

st.set_page_config(page_title="門診無菌處置室 - 語音耗材定位與庫存管理", layout="wide")

if "current_result" not in st.session_state:
    st.session_state.current_result = None

st.title("🏥 門診無菌處置室 — 智慧語音耗材定位與庫存系統")

# ================= 左側邊欄：語音指令控制台 =================
with st.sidebar:
    st.header("🎙️ 語音指令模擬控制台")
    
    preset_commands = [
        "請幫我拿 50cc 針筒",
        "給我一條止血帶",
        "拿 2 包無菌紗布",
        "給我縫合器械包",
        "生理食鹽水在哪裡",
        "快拿腎上腺素！病人過敏休克"
    ]
    selected_preset = st.selectbox("選擇預設臨床語音指令：", preset_commands)
    custom_input = st.text_input("或手動輸入模擬語音文字：", value=selected_preset)
    
    auto_deduct_mode = st.checkbox("開啟「語音同時自動扣庫存」模式", value=True)

    if st.button("⚡ 發送語音指令", type="primary", use_container_width=True):
        if custom_input.strip():
            res = search_supply_by_text(custom_input, auto_deduct=auto_deduct_mode)
            st.session_state.current_result = res

    st.divider()
    st.markdown("""
    **🗄️ 櫃位配置一覽：**
    - **A1櫃**：各式針筒
    - **A2櫃**：留置針、採血管、止血帶
    - **A3櫃**：無菌紗布、消毒棉片、紙膠、手套
    - **A4櫃**：縫合器械包、縫線、刀片、食鹽水
    - **A5櫃**：緊急處置備品（高風險警示）
    """)

# ================= 主畫面雙分頁切換 =================
tab_main, tab_admin = st.tabs(["🗄️ A1~A5 櫃位定位與領用", "🛠️ 庫存補貨與新增耗材後台"])

with tab_main:
    col_map, col_info = st.columns([1.4, 1])

    active_cabinet = None
    if st.session_state.current_result and st.session_state.current_result.get("found"):
        active_cabinet = st.session_state.current_result["data"]["cabinet_id"]

    # 從資料庫動態抓取每個櫃子目前放了哪些物品，直接顯示在櫃子卡片裡
    all_supplies = get_all_supplies()
    cab_items_map = {f"A{i}櫃": [] for i in range(1, 6)}
    for row in all_supplies:
        cab_id = row[3]
        if cab_id in cab_items_map:
            cab_items_map[cab_id].append(row[1])

    def render_cabinet_card(cab_id, subtitle, is_emergency=False):
        is_target = (active_cabinet == cab_id)
        if is_target:
            bg_color = "#dc3545" if is_emergency else "#28a745"
            border = "2px solid #ffffff"
            text_color = "#ffffff"
            badge = "🚨 緊急備品櫃" if is_emergency else "✔ 目標櫃位"
        else:
            bg_color = "#2b1618" if is_emergency else "#1e1f26"
            border = "1px solid #662222" if is_emergency else "1px solid #444444"
            text_color = "#cccccc"
            badge = "未選取"

        items_list_str = "、".join(cab_items_map.get(cab_id, [])) or "（尚無物品）"

        return f"""
        <div style="background-color:{bg_color}; color:{text_color}; border:{border}; 
                    border-radius:12px; padding:14px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="font-size:17px;">🗄️ {cab_id} — {subtitle}</strong>
                <span style="font-size:12px; background:rgba(0,0,0,0.4); padding:3px 8px; border-radius:5px;">{badge}</span>
            </div>
            <div style="font-size:13px; margin-top:8px; opacity:0.95;">
                <strong>櫃內物品：</strong>{items_list_str}
            </div>
        </div>
        """

    with col_map:
        st.subheader("🗄️ 處置室 A1 ~ A5 櫃位配置圖")
        
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1:
            st.markdown(render_cabinet_card("A1櫃", "注射針筒類"), unsafe_allow_html=True)
        with r1_c2:
            st.markdown(render_cabinet_card("A2櫃", "採血與留置針類"), unsafe_allow_html=True)

        r2_c1, r2_c2 = st.columns(2)
        with r2_c1:
            st.markdown(render_cabinet_card("A3櫃", "無菌紗布與敷料類"), unsafe_allow_html=True)
        with r2_c2:
            st.markdown(render_cabinet_card("A4櫃", "縫合器械與輸液類"), unsafe_allow_html=True)

        st.markdown(render_cabinet_card("A5櫃", "緊急處置專櫃（高風險警示）", is_emergency=True), unsafe_allow_html=True)

    with col_info:
        st.subheader("📦 查詢結果與即時庫存")
        res = st.session_state.current_result

        if res is None:
            st.info("👈 請從左側發送語音指令，系統將自動標示對應櫃號並更新庫存。")
        elif not res["found"]:
            st.error(f"❌ 資料庫查無符合「{res['raw_text']}」的耗材，請至後台新增。")
        else:
            item = res["data"]
            st.success(f"✅ 已鎖定耗材：**{item['item_name']}**")
            
            m1, m2 = st.columns(2)
            m1.metric("存放櫃位", item["cabinet_id"])
            m2.metric("目前剩餘庫存", f"{item['stock_qty']} 單位", delta=f"安全下限: {item['min_stock']}", delta_color="off")

            if item["is_low_stock"]:
                st.error(f"⚠️ **低庫存補貨警告**：目前僅剩 {item['stock_qty']} 單位（低於安全庫存 {item['min_stock']}），請至「庫存補貨後台」補貨！")
            else:
                st.caption("🟢 庫存狀態充足，符合安全存量標準。")

            st.divider()
            if item["stock_qty"] > 0:
                if st.button("📥 額外再拿取 1 單位（手動扣減庫存 -1）", use_container_width=True):
                    updated = deduct_supply_stock(item["item_id"], item["item_name"], qty=1)
                    if updated:
                        st.session_state.current_result = {"found": True, "data": updated}
                        st.rerun()
            else:
                st.warning("🚫 該櫃位目前庫存為 0，無法再扣除！請至管理後台補貨。")

    st.divider()
    st.subheader("📋 系統語音查詢與領用稽核日誌 (SQLite 即時紀錄)")
    logs = get_recent_logs(limit=6)
    if logs:
        df_logs = pd.DataFrame(logs, columns=["時間 (台灣時間)", "語音原始指令", "匹配耗材", "庫存動作", "狀態"])
        st.dataframe(df_logs, use_container_width=True, hide_index=True)

# ---------------- 分頁 2：庫存補貨與新增耗材後台 ----------------
with tab_admin:
    st.subheader("🛠️ 處置室耗材庫存管理與一鍵補貨")
    
    if st.button("⚡ 一鍵補滿所有「低於安全下限」的耗材", type="primary"):
        count = restock_all_low_items()
        if count > 0:
            st.success(f"✅ 已將 {count} 項低庫存耗材補滿至安全存量的 2 倍！")
            st.rerun()
        else:
            st.info("目前所有耗材庫存皆充足，無需補貨。")

    st.divider()
    admin_left, admin_right = st.columns([1.4, 1])

    df_supplies = pd.DataFrame(
        all_supplies,
        columns=["ID", "耗材名稱", "語音別名", "存放櫃位", "目前庫存", "安全下限"]
    )

    with admin_left:
        st.markdown("#### 1️⃣ 單一品項快速補貨")
        r_c1, r_c2, r_c3 = st.columns([2, 1, 1])
        item_options = {f"{row[1]} (剩 {row[4]} / 下限 {row[5]})": (row[0], row[1]) for row in all_supplies}
        selected_item_label = r_c1.selectbox("選擇要補貨的耗材：", list(item_options.keys()))
        add_amount = r_c2.number_input("補貨數量：", min_value=1, max_value=200, value=10, step=1)
        
        r_c3.write("")
        r_c3.write("")
        if r_c3.button("➕ 確認補貨", use_container_width=True):
            target_id, target_name = item_options[selected_item_label]
            restock_single_item(target_id, target_name, add_amount)
            st.success(f"✅ 已為「{target_name}」補貨 +{add_amount} 單位！")
            st.rerun()

        st.markdown("#### 📊 全室耗材即時庫存總表")
        df_display = df_supplies[["存放櫃位", "耗材名稱", "目前庫存", "安全下限"]].copy()
        df_display["狀態"] = df_display.apply(lambda r: "⚠️ 需補貨" if r["目前庫存"] < r["安全下限"] else "🟢 充足", axis=1)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    with admin_right:
        st.markdown("#### 2️⃣ 新增全新耗材品項")
        with st.form("add_supply_form", clear_on_submit=True):
            new_name = st.text_input("耗材正式名稱 *", placeholder="例如：1ml 胰島素空針")
            new_aliases = st.text_input("語音辨識別名（逗號分隔）*", placeholder="例如：1ml針筒,1cc針筒,胰島素針筒")
            new_cabinet = st.selectbox("存放櫃位：", ["A1櫃", "A2櫃", "A3櫃", "A4櫃", "A5櫃"])
            
            q1, q2 = st.columns(2)
            new_stock = q1.number_input("初始庫存：", min_value=1, value=20)
            new_min = q2.number_input("安全下限：", min_value=1, value=5)

            if st.form_submit_button("💾 寫入資料庫並啟用語音查詢", type="primary", use_container_width=True):
                if new_name.strip() and new_aliases.strip():
                    add_new_supply_item(new_name.strip(), new_aliases.strip(), new_cabinet, new_stock, new_min)
                    st.success(f"✅ 已新增「{new_name}」至 {new_cabinet}！")
                    st.rerun()
                else:
                    st.error("❌ 請填寫「耗材正式名稱」與「語音辨識別名」！")
import sqlite3
import json
import os

CONFIG_FILE = 'config.json'
DB_FILE = 'database.db'

def migrate_data():
    # Ktra tep can thiet
    if not os.path.exists(CONFIG_FILE):
        print(f"Lỗi: Không tìm thấy tệp '{CONFIG_FILE}'. Hãy đặt nó vào cùng thư mục.")
        return
    if not os.path.exists(DB_FILE):
        print(f"Lỗi: Không tìm thấy tệp '{DB_FILE}'. Hãy chạy bot chính một lần để tạo nó.")
        return

    # Lay Guild ID tu user
    guild_id_str = input(">>> Vui lòng nhập ID Server (Guild ID) của bạn và nhấn Enter: ")
    try:
        guild_id = int(guild_id_str)
    except ValueError:
        print("Lỗi: ID Server phải là một con số.")
        return

    # Doc file config
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print("Đã đọc xong file config.json...")

    conn = None
    try:
        # Ket noi DB
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # --- PHẦN 1: Di chuyển cài đặt Server ---
        print("Đang di chuyển cài đặt server...")
        cursor.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))

        settings_to_update = {
            'cfs_channel_id': config.get('TARGET_CHANNEL_ID'),
            'welcome_enabled': int(config.get('welcome_settings', {}).get('enabled', 0)),
            'welcome_channel_id': config.get('welcome_settings', {}).get('channel_id'),
            'welcome_rules_channel_id': config.get('welcome_settings', {}).get('rules_channel_id'),
            'welcome_lead_role_id': config.get('welcome_settings', {}).get('lead_role_id'),
            'welcome_title': config.get('welcome_settings', {}).get('title'),
            'welcome_message': config.get('welcome_settings', {}).get('message'),
            'welcome_image_url': config.get('welcome_settings', {}).get('image_url'),
            'leave_enabled': int(config.get('leave_settings', {}).get('enabled', 0)),
            'leave_channel_id': config.get('leave_settings', {}).get('channel_id'),
            'leave_title': config.get('leave_settings', {}).get('title'),
            'leave_message': config.get('leave_settings', {}).get('message'),
            'leave_image_url': config.get('leave_settings', {}).get('image_url'),
            'boost_enabled': int(config.get('boost_settings', {}).get('enabled', 0)),
            'boost_channel_id': config.get('boost_settings', {}).get('channel_id'),
            'boost_message': config.get('boost_settings', {}).get('message'),
            'boost_image_url': config.get('boost_settings', {}).get('image_url')
        }

        update_clauses = [f"{key} = ?" for key in settings_to_update.keys()]
        sql_query = f"UPDATE guild_settings SET {', '.join(update_clauses)} WHERE guild_id = ?"
        sql_values = list(settings_to_update.values())
        sql_values.append(guild_id)

        cursor.execute(sql_query, tuple(sql_values))
        conn.commit()
        print("-> Đã di chuyển cài đặt server thành công.")

        # --- PHẦN 2: Cập nhật số đếm confession ---
        print("Đang cập nhật số đếm confession...")
        # Lệnh INSERT OR REPLACE sẽ tạo mới nếu chưa có, hoặc thay thế nếu đã có.
        cursor.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('cfs_counter', '61')")
        conn.commit()
        print("-> Đã đặt lại số đếm confession thành 61.")
        
        # --- Hoàn tất ---
        print("\n-----------------------------------------")
        print(f"✅ HOÀN TẤT! Đã di chuyển và cập nhật dữ liệu thành công.")
        print(f"   - Cài đặt từ '{CONFIG_FILE}' đã được áp dụng cho Server ID: {guild_id}")
        print(f"   - Số đếm confession đã được đặt thành 61.")
        print("-----------------------------------------")

    except sqlite3.Error as e:
        print(f"Lỗi SQLite: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_data()
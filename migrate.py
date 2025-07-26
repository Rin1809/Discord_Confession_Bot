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

        # Dam bao guild co trong DB
        cursor.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))

        # Chuan bi du lieu de update
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

        # Tao cau lenh SQL
        update_clauses = [f"{key} = ?" for key in settings_to_update.keys()]
        sql_query = f"UPDATE guild_settings SET {', '.join(update_clauses)} WHERE guild_id = ?"

        # Tao tuple gia tri
        sql_values = list(settings_to_update.values())
        sql_values.append(guild_id)

        # Thuc thi
        cursor.execute(sql_query, tuple(sql_values))
        conn.commit()
        
        print("\n-----------------------------------------")
        print(f"✅ THÀNH CÔNG! Đã di chuyển dữ liệu từ '{CONFIG_FILE}' vào '{DB_FILE}' cho Server ID: {guild_id}")
        print("-----------------------------------------")

    except sqlite3.Error as e:
        print(f"Lỗi SQLite: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_data()
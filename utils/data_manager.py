import aiosqlite
import json

DB_FILE = 'database.db'

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    async def execute(self, query, params=(), fetch=None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                if fetch == 'one':
                    result = await cursor.fetchone()
                elif fetch == 'all':
                    result = await cursor.fetchall()
                else:
                    result = None
                await db.commit()
                return result

    async def setup_database(self):
        await self.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            cfs_channel_id INTEGER,
            welcome_enabled INTEGER DEFAULT 0, welcome_channel_id INTEGER, welcome_rules_channel_id INTEGER,
            welcome_lead_role_id INTEGER, welcome_title TEXT, welcome_message TEXT, welcome_image_url TEXT,
            leave_enabled INTEGER DEFAULT 0, leave_channel_id INTEGER, leave_title TEXT,
            leave_message TEXT, leave_image_url TEXT,
            boost_enabled INTEGER DEFAULT 0, boost_channel_id INTEGER, boost_message TEXT, boost_image_url TEXT
        )
        """)
        
        await self.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await self.execute("""
        CREATE TABLE IF NOT EXISTS anon_thread_data (
            thread_id INTEGER PRIMARY KEY,
            data TEXT
        )
        """)
        print("Database da san sang voi cau truc moi.")

    async def get_all_settings(self, guild_id):
        await self.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
        row = await self.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,), fetch='one')
        return dict(row) if row else {}

    async def get_setting(self, guild_id, key):
        row = await self.execute(f"SELECT {key} FROM guild_settings WHERE guild_id = ?", (guild_id,), fetch='one')
        return row[key] if row and row[key] is not None else None

    async def set_setting(self, guild_id, key, value):
        await self.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
        await self.execute(f"UPDATE guild_settings SET {key} = ? WHERE guild_id = ?", (value, guild_id))

    async def get_cfs_counter(self):
        row = await self.execute("SELECT value FROM bot_settings WHERE key = 'cfs_counter'", fetch='one')
        if row and row['value']:
            return int(row['value'])
        await self.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('cfs_counter', '1')")
        return 1

    async def increment_cfs_counter(self):
        current_value = await self.get_cfs_counter()
        new_value = current_value + 1
        await self.execute("UPDATE bot_settings SET value = ? WHERE key = 'cfs_counter'", (str(new_value),))
        return new_value
        
    async def get_anon_thread_data(self, thread_id: int):
        row = await self.execute("SELECT data FROM anon_thread_data WHERE thread_id = ?", (thread_id,), fetch='one')
        if row and row['data']:
            return json.loads(row['data'])
        return None

    async def save_anon_thread_data(self, thread_id: int, data: dict):
        json_data = json.dumps(data)
        await self.execute("INSERT OR REPLACE INTO anon_thread_data (thread_id, data) VALUES (?, ?)", (thread_id, json_data))
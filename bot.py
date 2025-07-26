import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from utils.data_manager import DatabaseManager, DB_FILE

load_dotenv()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.db = DatabaseManager(DB_FILE)

    async def setup_hook(self):
        await self.db.setup_database()
        
        print("Dang tai cac cogs...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'-> Da tai {filename}')
                except Exception as e:
                    print(f'Loi khi tai {filename}: {e}')
        
        try:
            synced = await self.tree.sync()
            print(f"Da dong bo {len(synced)} lenh slash.")
        except Exception as e:
            print(f"Loi khi dong bo lenh: {e}")

async def main():
    bot = MyBot()
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("Lỗi: Vui lòng thêm DISCORD_TOKEN vào file .env.")
        return
    
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot da tat.")
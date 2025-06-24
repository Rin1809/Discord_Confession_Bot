import discord
import os
import json
from discord import app_commands, ui

# --- ham xu ly ---

def load_config():
    # load file config
    if not os.path.exists('config.json'):
        print("Loi: File config.json khong ton tai. Vui long tao file.")
        return None
    with open('config.json', 'r') as f:
        return json.load(f)

def load_counter(path):
    # load so dem tu file
    try:
        with open(path, 'r') as f:
            return int(f.read())
    except (FileNotFoundError, ValueError):
        # neu file k ton tai hoac rong, tao moi
        with open(path, 'w') as f:
            f.write('1')
        return 1

def save_counter(path, value):
    # luu so dem
    with open(path, 'w') as f:
        f.write(str(value))

# --- khoi tao bot ---

config = load_config()

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        await self.tree.sync()
        print(f'Da dang nhap voi ten {self.user}')
        print('Bot san sang!')

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

# --- modal gui cfs ---

class ConfessionModal(ui.Modal, title='Gui Confession cua ban'):
    content = ui.TextInput(
        label='Noi dung Confession',
        style=discord.TextStyle.long,
        placeholder='Nhap confession cua ban o day...',
        required=True,
        max_length=2000,
    )

    def __init__(self, target_channel: discord.TextChannel, counter_path: str, image: discord.Attachment = None):
        super().__init__()
        self.target_channel = target_channel
        self.counter_path = counter_path
        self.image = image

    async def on_submit(self, interaction: discord.Interaction):
        # lay so dem hien tai
        current_cfs_number = load_counter(self.counter_path)
        
        # tao embed
        embed = discord.Embed(
            title=f"Confession #{current_cfs_number}",
            description=self.content.value,
            color=discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="Gui boi mot nguoi an danh")

        if self.image:
            if self.image.content_type.startswith('image/'):
                embed.set_image(url=self.image.url)
            else:
                await interaction.response.send_message("Loi: Tep dinh kem phai la hinh anh.", ephemeral=True)
                return

        try:
            sent_message = await self.target_channel.send(embed=embed)
            
            # tao thread
            await sent_message.create_thread(
                name=f"Thao luan CFS #{current_cfs_number}",
                auto_archive_duration=10080
            )
            
            await interaction.response.send_message(f'✅ Confession #{current_cfs_number} da duoc gui thanh cong!', ephemeral=True)
            
            # tang & luu so dem
            save_counter(self.counter_path, current_cfs_number + 1)

        except discord.Forbidden:
            await interaction.response.send_message("Loi: Bot khong co quyen trong kenh confession.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Da co loi xay ra: {e}", ephemeral=True)
            print(f"Loi chi tiet: {e}")

# --- lenh slash ---

@client.tree.command(name="cfs", description="Gui mot confession an danh vao kenh duoc chi dinh")
@app_commands.describe(
    image="(Tuy chon) Dinh kem mot hinh anh vao confession"
)
async def confession(interaction: discord.Interaction, image: discord.Attachment = None):
    target_channel = client.get_channel(config['TARGET_CHANNEL_ID'])

    if not target_channel:
        await interaction.response.send_message("Loi: Khong tim thay kenh confession. Kiem tra TARGET_CHANNEL_ID trong config.json.", ephemeral=True)
        return

    modal = ConfessionModal(
        target_channel=target_channel,
        counter_path=config['COUNTER_FILE_PATH'],
        image=image
    )
    await interaction.response.send_modal(modal)

# --- chay bot ---

if __name__ == "__main__":
    if config:
        TOKEN = config.get('DISCORD_TOKEN')
        if TOKEN and TOKEN != "MA_TOKEN_CUA_BAN_O_DAY":
            client.run(TOKEN)
        else:
            print("Loi: Vui long them DISCORD_TOKEN vao file config.json.")
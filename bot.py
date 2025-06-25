import discord
import os
import json
import random 
from discord import app_commands, ui
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import zoneinfo

# dinh nghia ham load/save json
def load_json_data(filepath):
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json_data(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

load_dotenv()

config = load_json_data('config.json')
ANON_USERS_FILE = config['ANON_USERS_FILE']

PREDEFINED_COLORS = [
    0x3498db, 0x2ecc71, 0xf1c40f, 0xe91e63, 0x9b59b6,
    0x1abc9c, 0xf39c12, 0x34495e, 0xad1457, 0x607d8b
]

anon_users_data = load_json_data(ANON_USERS_FILE)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("Loi: Vui long them GEMINI_API_KEY vao file .env.")
    exit()

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

def load_counter(path):
    try:
        with open(path, 'r', encoding='utf-8') as f: return int(f.read())
    except (FileNotFoundError, ValueError):
        with open(path, 'w', encoding='utf-8') as f: f.write('1')
        return 1

def save_counter(path, value):
    with open(path, 'w', encoding='utf-8') as f: f.write(str(value))

def get_anonymous_identity(user_id_str: str, thread_data: dict):
    if user_id_str == str(thread_data["op_user_id"]):
        return "Chủ thớt (OP)", discord.Color.gold()
    
    if user_id_str in thread_data["users"]:
        user_data = thread_data["users"][user_id_str]
        return user_data["id"], discord.Color(user_data["color"])
    
    new_anon_number = thread_data.get("counter", 1)
    anon_name = f"Người lạ #{new_anon_number}"
    color_value = random.choice(PREDEFINED_COLORS)
    
    thread_data["users"][user_id_str] = {"id": anon_name, "color": color_value}
    thread_data["counter"] = new_anon_number + 1
    
    return anon_name, discord.Color(color_value)

async def update_sticky_prompt(thread: discord.Thread, all_data: dict):
    thread_id_str = str(thread.id)

    if thread_id_str not in all_data:
        return

    old_prompt_id = all_data[thread_id_str].get("last_prompt_message_id")
    if old_prompt_id:
        try:
            old_prompt_msg = await thread.fetch_message(old_prompt_id)
            await old_prompt_msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    new_prompt_msg = await thread.send(
        "Nhấn nút bên dưới nếu muốn trả lời ẩn danh.👇",
        view=PersistentReplyView()
    )
    all_data[thread_id_str]["last_prompt_message_id"] = new_prompt_msg.id

async def handle_anonymous_reply(interaction: discord.Interaction, content: str, target_message: discord.Message = None):
    current_anon_data = load_json_data(ANON_USERS_FILE)
    thread_id_str = str(interaction.channel.id)
    user_id_str = str(interaction.user.id)
    
    if thread_id_str not in current_anon_data:
        return

    thread_data = current_anon_data[thread_id_str]
    anon_name, anon_color = get_anonymous_identity(user_id_str, thread_data)
    
    description = content
    
    if target_message and target_message.embeds:
        replied_embed = target_message.embeds[0]
        replied_author = replied_embed.author.name or "ẩn danh"
        full_description = replied_embed.description
        
        if '\n\n' in full_description and full_description.startswith('>'):
            content_part = full_description.split('\n\n', 1)[1]
        else:
            content_part = full_description
            
        quote = content_part.split('\n')[0]
        if len(quote) > 70: quote = quote[:70] + "..."
        
        description = f"> **Trả lời {replied_author}**: *{quote}*\n\n{content}"

    embed = discord.Embed(
        description=description, color=anon_color, 
        timestamp=datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh"))
    )
    embed.set_author(name=anon_name)
    
    await interaction.channel.send(embed=embed, view=AnonMessageView())
    await update_sticky_prompt(interaction.channel, current_anon_data)
    save_json_data(ANON_USERS_FILE, current_anon_data)

class DirectReplyModal(ui.Modal, title='Trả lời trực tiếp'):
    reply_content = ui.TextInput(label='Nội dung trả lời', style=discord.TextStyle.long, required=True, max_length=2000)

    def __init__(self, target_message: discord.Message):
        super().__init__()
        self.target_message = target_message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await handle_anonymous_reply(interaction, self.reply_content.value, self.target_message)
        await interaction.followup.send('Đã gửi trả lời của bạn!', ephemeral=True)

class AnonMessageView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='⮤ Trả lời', style=discord.ButtonStyle.secondary, custom_id='direct_reply_button')
    async def direct_reply(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(DirectReplyModal(target_message=interaction.message))

class GeneralReplyModal(ui.Modal, title='Trả lời ẩn danh'):
    reply_content = ui.TextInput(label='Nội dung trả lời', style=discord.TextStyle.long, required=True, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await handle_anonymous_reply(interaction, self.reply_content.value)
        await interaction.followup.send('Đã gửi trả lời của bạn!', ephemeral=True)

class PersistentReplyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='✍️ Trả lời ẩn danh', style=discord.ButtonStyle.green, custom_id='persistent_general_reply_button')
    async def general_reply_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(GeneralReplyModal())

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        self.add_view(PersistentReplyView())
        self.add_view(AnonMessageView())
        await self.tree.sync()
        activity = discord.Activity(name="/cfs để gửi confession", type=discord.ActivityType.watching)
        await client.change_presence(activity=activity)
        print(f'Da dang nhap voi ten {self.user}')
        print('Bot san sang!')

intents = discord.Intents.default()
client = MyClient(intents=intents)

class ConfessionModal(ui.Modal, title='Gửi Confession của bạn'):
    title_input = ui.TextInput(label='Tiêu đề (Tùy chọn)', placeholder='Nhập tiêu đề...', required=False, max_length=100)
    content = ui.TextInput(label='Nội dung Confession', style=discord.TextStyle.long, placeholder='Viết confession của bạn ở đây...', required=True, max_length=4000)

    def __init__(self, target_channel: discord.TextChannel, counter_path: str, attachment: discord.Attachment = None):
        super().__init__()
        self.target_channel = target_channel
        self.counter_path = counter_path
        self.attachment = attachment

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        current_cfs_number = load_counter(self.counter_path)
        original_content = self.content.value
        formatted_content = original_content

        try:
            prompt = (
                "Định dạng văn bản sau bằng markdown (quan trọng, luôn luôn phải có. in đậm, v.v... các xuống hàng, phân tách nội dung v.v....), chỉnh sửa bố cục"
                "LƯU Ý: không được thêm thắt nội dung, chỉ cần viết lại với định dạng markdow, chỉnh sửa bố cục đẹp mắt dễ đọc và chuyên nghiệp một cách phù hợp với nội dung."
                "Giữ nguyên ngôn ngữ gốc. Không thêm bình luận cá nhân của bạn vào output. "
                f"Văn bản: \"{original_content}\""
            )
            response = gemini_model.generate_content(prompt)
            formatted_content = response.text
        except Exception as e:
            print(f"Loi Gemini: {e}. Dung noi dung goc.")
            await interaction.followup.send(
                "⚠️ Đã có lỗi khi định dạng confession của bạn bằng AI. "
                "Confession vẫn được gửi với nội dung gốc.", 
                ephemeral=True
            )

        user_title = self.title_input.value
        timestamp_str = datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %I:%M %p")
        guild_icon_url = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else ""
        
        title_separator = "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        
        if user_title:
            final_description = title_separator + formatted_content
        else:
            final_description = formatted_content
        
        is_image = self.attachment and self.attachment.content_type and self.attachment.content_type.startswith('image/')

        random_color = discord.Color(random.randint(0, 0xFFFFFF))
        embed = discord.Embed(title=user_title if user_title else None, description=final_description, color=random_color)
        
        author_name = f"Confession #{current_cfs_number} • {timestamp_str}"
        embed.set_author(name=author_name, icon_url=guild_icon_url)
        footer_text = "Được gửi ẩn danh bởi Yumemi-chan"
        bot_avatar_url = client.user.display_avatar.url
        embed.set_footer(text=footer_text, icon_url=bot_avatar_url)
        
        file_to_send = None
        if self.attachment:
            if is_image:
                file_to_send = await self.attachment.to_file()
                embed.set_image(url=f"attachment://{self.attachment.filename}")
            elif self.attachment.content_type and (self.attachment.content_type.startswith('video/') or self.attachment.content_type.startswith('audio/')):
                file_to_send = await self.attachment.to_file()
            else:
                await interaction.followup.send("Lỗi: Loại tệp không được hỗ trợ.", ephemeral=True)
                return

        try:
            sent_message = await self.target_channel.send(embed=embed, file=file_to_send)
            new_thread = await sent_message.create_thread(name=f"Trả lời, tham gia thảo luận CFS #{current_cfs_number} tại đây", auto_archive_duration=10080)
            
            prompt_msg = await new_thread.send(
                "Nhấn nút bên dưới nếu muốn trả lời ẩn danh👇", 
                view=PersistentReplyView()
            )

            all_data = load_json_data(ANON_USERS_FILE)
            all_data[str(new_thread.id)] = {
                "op_user_id": interaction.user.id,
                "users": {},
                "counter": 1,
                "last_prompt_message_id": prompt_msg.id
            }
            save_json_data(ANON_USERS_FILE, all_data)
            
            await interaction.followup.send(f'✅ Confession #{current_cfs_number} đã được gửi!', ephemeral=True)
            save_counter(self.counter_path, current_cfs_number + 1)
        except Exception as e:
            await interaction.followup.send(f"Đã có lỗi xảy ra: {e}", ephemeral=True)
            print(f"Loi chi tiet: {e}")

@client.tree.command(name="cfs", description="Gửi một confession ẩn danh vào kênh được chỉ định")
@app_commands.describe(attachment="(Tùy chọn) Đính kèm một tệp (ảnh, video, audio)")
async def confession(interaction: discord.Interaction, attachment: discord.Attachment = None):
    target_channel_id = int(os.getenv('TARGET_CHANNEL_ID'))
    target_channel = client.get_channel(target_channel_id)
    if not target_channel:
        await interaction.response.send_message("Lỗi: Không tìm thấy kênh confession.", ephemeral=True)
        return
    modal = ConfessionModal(target_channel=target_channel, counter_path=config['COUNTER_FILE_PATH'], attachment=attachment)
    await interaction.response.send_modal(modal)

if __name__ == "__main__":
    if config:
        TOKEN = os.getenv('DISCORD_TOKEN')
        if TOKEN:
            client.run(TOKEN)
        else:
            print("Lỗi: Vui lòng thêm DISCORD_TOKEN vào file .env.")
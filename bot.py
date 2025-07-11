import discord
import os
import json
import random 
from discord import app_commands, ui
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import zoneinfo

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
ANON_USERS_FILE = config.get('ANON_USERS_FILE', 'anonymous_users.json')

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

    @ui.button(label='Trả lời', style=discord.ButtonStyle.secondary, custom_id='direct_reply_button')
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

    async def setup_hook(self) -> None:
        self.add_view(PersistentReplyView())
        self.add_view(AnonMessageView())
        await self.tree.sync()

    async def on_ready(self):
        activity = discord.Activity(name="/cfs để gửi confession", type=discord.ActivityType.watching)
        await client.change_presence(activity=activity)
        print(f'Da dang nhap voi ten {self.user}')
        print('Bot san sang!')
    
    async def on_member_join(self, member: discord.Member):
        global config
        config = load_json_data('config.json') 
        
        welcome_config = config.get("welcome_settings", {})
        if not welcome_config.get("enabled") or not welcome_config.get("channel_id"):
            return

        channel = member.guild.get_channel(welcome_config["channel_id"])
        if not channel:
            return

        title_template = welcome_config.get("title", "Chào mừng {user.display_name}!")
        message_template = welcome_config.get("message", "Chào mừng {user.mention}!")
        image_url = welcome_config.get("image_url")
        rules_id = welcome_config.get("rules_channel_id")
        lead_id = welcome_config.get("lead_role_id")
        color_value = welcome_config.get("color", 0xFFB6C1)

        try:
            msg_with_ids = message_template
            if rules_id:
                msg_with_ids = msg_with_ids.replace("{rules_channel_id}", str(rules_id))
            if lead_id:
                msg_with_ids = msg_with_ids.replace("{lead_role_id}", str(lead_id))

            final_title = title_template.format(user=member, server=member.guild)
            final_message = msg_with_ids.format(user=member, server=member.guild)

            embed = discord.Embed(
                title=final_title,
                description=final_message,
                color=discord.Color(color_value)
            )
            
            if member.guild.icon:
                embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)
            
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            
            if image_url:
                embed.set_image(url=image_url)

            await channel.send(embed=embed)
        except Exception as e:
            print(f"Loi khi gui tin chao mung: {e}")

    async def on_member_remove(self, member: discord.Member):
        global config
        config = load_json_data('config.json')
        
        leave_config = config.get("leave_settings", {})
        if not leave_config.get("enabled") or not leave_config.get("channel_id"):
            return

        channel = member.guild.get_channel(leave_config["channel_id"])
        if not channel:
            return

        title_template = leave_config.get("title", "{user.display_name} đã rời đi")
        message_template = leave_config.get("message", "Tạm biệt bạn.")
        image_url = leave_config.get("image_url")
        color_value = leave_config.get("color", 0xFFB6C1)
        
        try:
            final_title = title_template.format(user=member, server=member.guild)
            final_message = message_template.format(user=member, server=member.guild)

            embed = discord.Embed(
                title=final_title,
                description=final_message,
                color=discord.Color(color_value)
            )

            if member.guild.icon:
                embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)

            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)

            if image_url:
                embed.set_image(url=image_url)
            
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Loi khi gui tin roi di: {e}")

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.premium_since is None and after.premium_since is not None:
            global config
            config = load_json_data('config.json')

            boost_config = config.get("boost_settings", {})
            if not boost_config.get("enabled") or not boost_config.get("channel_id"):
                return
            
            channel = after.guild.get_channel(boost_config["channel_id"])
            if not channel:
                return

            message = boost_config.get("message", "Cảm ơn {user.mention} đã boost server!")
            image_url = boost_config.get("image_url")

            try:
                formatted_message = message.format(user=after, server=after.guild)
                embed = discord.Embed(description=formatted_message, color=discord.Color.magenta())
                embed.set_author(name=f"{after.display_name} vừa boost server!", icon_url=after.guild.icon.url if after.guild.icon else None)
                embed.set_thumbnail(url=after.display_avatar.url)
                if image_url:
                    embed.set_image(url=image_url)
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Loi khi gui tin boost: {e}")

intents = discord.Intents.default()
intents.members = True 
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
            prompt = ("Định dạng văn bản sau bằng markdown (quan trọng, luôn luôn phải có. in đậm, v.v... các xuống hàng, phân tách nội dung v.v....), chỉnh sửa bố cục""LƯU Ý: không được thêm thắt nội dung, chỉ cần viết lại với định dạng markdow, chỉnh sửa bố cục đẹp mắt dễ đọc và chuyên nghiệp một cách phù hợp với nội dung.""Giữ nguyên ngôn ngữ gốc. Không thêm bình luận cá nhân của bạn vào output. "f"Văn bản: \"{original_content}\"")
            response = gemini_model.generate_content(prompt)
            formatted_content = response.text
        except Exception as e:
            print(f"Loi Gemini: {e}. Dung noi dung goc.")
            await interaction.followup.send("⚠️ Đã có lỗi khi định dạng confession của bạn bằng AI. Confession vẫn được gửi với nội dung gốc.", ephemeral=True)
        user_title = self.title_input.value
        timestamp_str = datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %I:%M %p")
        guild_icon_url = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else ""
        title_separator = "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        final_description = (title_separator + formatted_content) if user_title else formatted_content
        is_image = self.attachment and self.attachment.content_type and self.attachment.content_type.startswith('image/')
        random_color = discord.Color(random.randint(0, 0xFFFFFF))
        embed = discord.Embed(title=user_title if user_title else None, description=final_description, color=random_color)
        author_name = f"Confession #{current_cfs_number} • {timestamp_str}"
        embed.set_author(name=author_name, icon_url=guild_icon_url)
        
        embed.set_footer(text="Được gửi ẩn danh bởi Yumemi-chan", icon_url=client.user.display_avatar.url)
        footer_text = "Được gửi ẩn danh bởi Yumemi-chan\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\nGõ lệnh /cfs để gửi confession"
        embed.set_footer(text=footer_text, icon_url=client.user.display_avatar.url)
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
            prompt_msg = await new_thread.send("Nhấn nút bên dưới nếu muốn trả lời ẩn danh👇", view=PersistentReplyView())
            all_data = load_json_data(ANON_USERS_FILE)
            all_data[str(new_thread.id)] = {"op_user_id": interaction.user.id, "users": {}, "counter": 1, "last_prompt_message_id": prompt_msg.id}
            save_json_data(ANON_USERS_FILE, all_data)
            await interaction.followup.send(f'✅ Confession #{current_cfs_number} đã được gửi!', ephemeral=True)
            save_counter(self.counter_path, current_cfs_number + 1)
        except Exception as e:
            await interaction.followup.send(f"Đã có lỗi xảy ra: {e}", ephemeral=True)
            print(f"Loi chi tiet: {e}")

class WelcomeMessageModal(ui.Modal, title='Thiết lập tin nhắn chào mừng'):
    message_content = ui.TextInput(label='Nội dung', style=discord.TextStyle.long, max_length=1000, placeholder='VD: Chào mừng {user.mention} đã đến với {server.name}!')
    async def on_submit(self, interaction: discord.Interaction):
        global config
        config.setdefault("welcome_settings", {})["message"] = self.message_content.value
        save_json_data('config.json', config)
        await interaction.response.send_message(f"✅ Đã cập nhật tin nhắn chào mừng.", ephemeral=True)

class LeaveMessageModal(ui.Modal, title='Thiết lập tin nhắn rời đi'):
    message_content = ui.TextInput(label='Nội dung', style=discord.TextStyle.long, max_length=1000, placeholder='VD: Tạm biệt {user.name}...')
    async def on_submit(self, interaction: discord.Interaction):
        global config
        config.setdefault("leave_settings", {})["message"] = self.message_content.value
        save_json_data('config.json', config)
        await interaction.response.send_message(f"✅ Đã cập nhật tin nhắn rời đi.", ephemeral=True)

class BoostMessageModal(ui.Modal, title='Thiết lập tin nhắn boost'):
    message_content = ui.TextInput(label='Nội dung', style=discord.TextStyle.long, max_length=1000, placeholder='VD: {user.mention} vừa boost server!')
    async def on_submit(self, interaction: discord.Interaction):
        global config
        config.setdefault("boost_settings", {})["message"] = self.message_content.value
        save_json_data('config.json', config)
        await interaction.response.send_message(f"✅ Đã cập nhật tin nhắn boost.", ephemeral=True)

@client.tree.command(name="cfs", description="Gửi một confession ẩn danh")
@app_commands.describe(attachment="(Tùy chọn) Đính kèm một tệp")
async def confession(interaction: discord.Interaction, attachment: discord.Attachment = None):
    target_channel_id = config.get('TARGET_CHANNEL_ID')
    if not target_channel_id:
        await interaction.response.send_message("Lỗi: Kênh confession chưa được thiết lập. Dùng `/setchannel`.", ephemeral=True)
        return
    target_channel = client.get_channel(target_channel_id)
    if not target_channel:
        await interaction.response.send_message("Lỗi: Không tìm thấy kênh confession.", ephemeral=True)
        return
    counter_path = config.get('COUNTER_FILE_PATH', 'counter.txt')
    await interaction.response.send_modal(ConfessionModal(target_channel=target_channel, counter_path=counter_path, attachment=attachment))

@client.tree.command(name="setchannel", description="Thiết lập kênh confession (Admin).")
@app_commands.describe(channel="Kênh để nhận confession.")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global config
    config['TARGET_CHANNEL_ID'] = channel.id
    save_json_data('config.json', config) 
    await interaction.response.send_message(f"✅ Đã thiết lập kênh confession là {channel.mention}.", ephemeral=True)

async def handle_permission_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Lỗi: Bạn không có quyền dùng lệnh này.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Lỗi: {error}", ephemeral=True)

welcome_group = app_commands.Group(name="welcome", description="Cài đặt chào mừng thành viên (Admin)")
@welcome_group.command(name="toggle", description="Bật/Tắt tính năng chào mừng.")
@app_commands.checks.has_permissions(administrator=True)
async def toggle_welcome(interaction: discord.Interaction):
    global config
    settings = config.setdefault("welcome_settings", {})
    settings["enabled"] = not settings.get("enabled", False)
    save_json_data('config.json', config)
    await interaction.response.send_message(f"✅ Đã **{'BẬT' if settings['enabled'] else 'TẮT'}** tính năng chào mừng.", ephemeral=True)
@welcome_group.command(name="setchannel", description="Chọn kênh chào mừng.")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global config
    config.setdefault("welcome_settings", {})["channel_id"] = channel.id
    save_json_data('config.json', config)
    await interaction.response.send_message(f"✅ Kênh chào mừng được đặt thành {channel.mention}.", ephemeral=True)
@welcome_group.command(name="setmessage", description="Tùy chỉnh tin nhắn chào mừng.")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome_message(interaction: discord.Interaction):
    await interaction.response.send_modal(WelcomeMessageModal())
client.tree.add_command(welcome_group)
@welcome_group.error
async def welcome_group_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await handle_permission_error(interaction, error)

leave_group = app_commands.Group(name="leave", description="Cài đặt thông báo thành viên rời đi (Admin)")
@leave_group.command(name="toggle", description="Bật/Tắt thông báo thành viên rời đi.")
@app_commands.checks.has_permissions(administrator=True)
async def toggle_leave(interaction: discord.Interaction):
    global config
    settings = config.setdefault("leave_settings", {})
    settings["enabled"] = not settings.get("enabled", False)
    save_json_data('config.json', config)
    await interaction.response.send_message(f"✅ Đã **{'BẬT' if settings['enabled'] else 'TẮT'}** tính năng thông báo rời đi.", ephemeral=True)
@leave_group.command(name="setchannel", description="Chọn kênh thông báo.")
@app_commands.checks.has_permissions(administrator=True)
async def set_leave_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global config
    config.setdefault("leave_settings", {})["channel_id"] = channel.id
    save_json_data('config.json', config)
    await interaction.response.send_message(f"✅ Kênh thông báo rời đi được đặt thành {channel.mention}.", ephemeral=True)
@leave_group.command(name="setmessage", description="Tùy chỉnh tin nhắn rời đi.")
@app_commands.checks.has_permissions(administrator=True)
async def set_leave_message(interaction: discord.Interaction):
    await interaction.response.send_modal(LeaveMessageModal())
client.tree.add_command(leave_group)
@leave_group.error
async def leave_group_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await handle_permission_error(interaction, error)

boost_group = app_commands.Group(name="boost", description="Cài đặt thông báo boost server (Admin)")
@boost_group.command(name="toggle", description="Bật/Tắt thông báo boost.")
@app_commands.checks.has_permissions(administrator=True)
async def toggle_boost(interaction: discord.Interaction):
    global config
    settings = config.setdefault("boost_settings", {})
    settings["enabled"] = not settings.get("enabled", False)
    save_json_data('config.json', config)
    await interaction.response.send_message(f"✅ Đã **{'BẬT' if settings['enabled'] else 'TẮT'}** tính năng thông báo boost.", ephemeral=True)
@boost_group.command(name="setchannel", description="Chọn kênh thông báo boost.")
@app_commands.checks.has_permissions(administrator=True)
async def set_boost_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global config
    config.setdefault("boost_settings", {})["channel_id"] = channel.id
    save_json_data('config.json', config)
    await interaction.response.send_message(f"✅ Kênh thông báo boost được đặt thành {channel.mention}.", ephemeral=True)
@boost_group.command(name="setmessage", description="Tùy chỉnh tin nhắn boost.")
@app_commands.checks.has_permissions(administrator=True)
async def set_boost_message(interaction: discord.Interaction):
    await interaction.response.send_modal(BoostMessageModal())
client.tree.add_command(boost_group)
@boost_group.error
async def boost_group_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await handle_permission_error(interaction, error)

if __name__ == "__main__":
    if config:
        TOKEN = os.getenv('DISCORD_TOKEN')
        if TOKEN:
            client.run(TOKEN)
        else:
            print("Lỗi: Vui lòng thêm DISCORD_TOKEN vào file .env.")
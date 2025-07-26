import discord
import os
import random
from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime
import zoneinfo
import google.generativeai as genai

PREDEFINED_COLORS = [0x3498db, 0x2ecc71, 0xf1c40f, 0xe91e63, 0x9b59b6, 0x1abc9c, 0xf39c12, 0x34495e, 0xad1457, 0x607d8b]

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

class PersistentReplyView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='✍️ Trả lời ẩn danh', style=discord.ButtonStyle.green, custom_id='persistent_general_reply_button')
    async def general_reply_button(self, interaction: discord.Interaction, button: ui.Button):
        # Callback nay se duoc ghi de trong Cog's setup
        pass

class AnonMessageView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='Trả lời', style=discord.ButtonStyle.secondary, custom_id='direct_reply_button')
    async def direct_reply(self, interaction: discord.Interaction, button: ui.Button):
        # Callback nay se duoc ghi de trong Cog's setup
        pass

def get_anonymous_identity(user_id_str: str, thread_data: dict):
    if user_id_str == str(thread_data.get("op_user_id")): return "Chủ thớt (OP)", discord.Color.gold()
    if user_id_str in thread_data.get("users", {}):
        user_data = thread_data["users"][user_id_str]
        return user_data["id"], discord.Color(user_data["color"])
    new_anon_number = thread_data.get("counter", 1)
    anon_name = f"Người lạ #{new_anon_number}"
    color_value = random.choice(PREDEFINED_COLORS)
    if "users" not in thread_data: thread_data["users"] = {}
    thread_data["users"][user_id_str] = {"id": anon_name, "color": color_value}
    thread_data["counter"] = new_anon_number + 1
    return anon_name, discord.Color(color_value)

async def update_sticky_prompt(db_manager, thread: discord.Thread):
    thread_data = await db_manager.get_anon_thread_data(thread.id)
    if not thread_data: return
    old_prompt_id = thread_data.get("last_prompt_message_id")
    if old_prompt_id:
        try:
            old_prompt_msg = await thread.fetch_message(old_prompt_id)
            await old_prompt_msg.delete()
        except (discord.NotFound, discord.Forbidden): pass
    new_prompt_msg = await thread.send("Nhấn nút bên dưới nếu muốn trả lời ẩn danh.👇", view=PersistentReplyView())
    thread_data["last_prompt_message_id"] = new_prompt_msg.id
    await db_manager.save_anon_thread_data(thread.id, thread_data)

async def handle_anonymous_reply(bot, interaction: discord.Interaction, content: str, target_message: discord.Message = None):
    thread_data = await bot.db.get_anon_thread_data(interaction.channel.id)
    if not thread_data: return
    anon_name, anon_color = get_anonymous_identity(str(interaction.user.id), thread_data)
    description = content
    if target_message and target_message.embeds:
        replied_embed = target_message.embeds[0]
        replied_author = replied_embed.author.name or "ẩn danh"
        full_description = replied_embed.description
        content_part = full_description.split('\n\n', 1)[-1]
        quote = content_part.split('\n')[0]
        if len(quote) > 70: quote = quote[:70] + "..."
        description = f"> **Trả lời {replied_author}**: *{quote}*\n\n{content}"
    embed = discord.Embed(description=description, color=anon_color, timestamp=datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")))
    embed.set_author(name=anon_name)
    await interaction.channel.send(embed=embed, view=AnonMessageView())
    await update_sticky_prompt(bot.db, interaction.channel)
    await bot.db.save_anon_thread_data(interaction.channel.id, thread_data)

class ReplyModal(ui.Modal):
    reply_content = ui.TextInput(label='Nội dung trả lời', style=discord.TextStyle.long, required=True, max_length=2000)
    def __init__(self, title: str, bot: commands.Bot, target_message: discord.Message = None):
        super().__init__(title=title)
        self.target_message = target_message
        self.bot = bot
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await handle_anonymous_reply(self.bot, interaction, self.reply_content.value, self.target_message)
        await interaction.followup.send('Đã gửi trả lời của bạn!', ephemeral=True)

class ConfessionModal(ui.Modal, title='Gửi Confession của bạn'):
    title_input = ui.TextInput(label='Tiêu đề (Tùy chọn)', required=False, max_length=100)
    content = ui.TextInput(label='Nội dung Confession', style=discord.TextStyle.long, required=True, max_length=4000)
    def __init__(self, target_channel: discord.TextChannel, bot: commands.Bot, attachment: discord.Attachment = None):
        super().__init__()
        self.target_channel = target_channel
        self.bot = bot
        self.attachment = attachment

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        current_cfs_number = await self.bot.db.get_cfs_counter()
        original_content = self.content.value
        formatted_content = original_content
        if gemini_model:
            try:
                prompt = (f'Định dạng lại văn bản sau bằng markdown cho đẹp mắt, dễ đọc. Giữ nguyên ngôn ngữ gốc và không thêm bất kỳ bình luận hay nội dung nào khác. Văn bản: "{original_content}"')
                response = await gemini_model.generate_content_async(prompt)
                formatted_content = response.text
            except Exception as e:
                print(f"Loi Gemini: {e}. Dung noi dung goc.")
                await interaction.followup.send("⚠️ Lỗi định dạng AI. Confession vẫn được gửi với nội dung gốc.", ephemeral=True)
        user_title = self.title_input.value
        timestamp_str = datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %I:%M %p")
        embed = discord.Embed(title=user_title or None, description=formatted_content, color=discord.Color(random.randint(0, 0xFFFFFF)))
        embed.set_author(name=f"Confession #{current_cfs_number} • {timestamp_str}", icon_url=interaction.guild.icon.url if interaction.guild.icon else "")
        embed.set_footer(text="Gõ lệnh /cfs để gửi confession", icon_url=self.bot.user.display_avatar.url)
        file_to_send = None
        if self.attachment:
            if self.attachment.content_type and (self.attachment.content_type.startswith(('image/', 'video/', 'audio/'))):
                file_to_send = await self.attachment.to_file()
                if self.attachment.content_type.startswith('image/'):
                    embed.set_image(url=f"attachment://{self.attachment.filename}")
            else:
                await interaction.followup.send("Lỗi: Loại tệp không được hỗ trợ.", ephemeral=True)
                return
        try:
            sent_message = await self.target_channel.send(embed=embed, file=file_to_send)
            thread_name = f"Thảo luận CFS #{current_cfs_number}: {user_title or original_content[:50]}"
            new_thread = await sent_message.create_thread(name=thread_name, auto_archive_duration=10080)
            initial_thread_data = {"op_user_id": interaction.user.id, "users": {}, "counter": 1}
            await self.bot.db.save_anon_thread_data(new_thread.id, initial_thread_data)
            await update_sticky_prompt(self.bot.db, new_thread)
            await interaction.followup.send(f'✅ Confession #{current_cfs_number} đã được gửi!', ephemeral=True)
            await self.bot.db.increment_cfs_counter()
        except Exception as e:
            await interaction.followup.send(f"Đã có lỗi xảy ra: {e}", ephemeral=True)
            print(f"Loi chi tiet khi gui cfs: {e}")

class ConfessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(PersistentReplyView())
        self.bot.add_view(AnonMessageView())

        # Ghi de callback cua button de truyen 'bot' vao modal
        PersistentReplyView.general_reply_button.callback = self.general_reply_callback
        AnonMessageView.direct_reply.callback = self.direct_reply_callback

    async def general_reply_callback(self, interaction: discord.Interaction, button: ui.Button):
        modal = ReplyModal(title='Trả lời ẩn danh', bot=self.bot)
        await interaction.response.send_modal(modal)

    async def direct_reply_callback(self, interaction: discord.Interaction, button: ui.Button):
        modal = ReplyModal(title='Trả lời trực tiếp', bot=self.bot, target_message=interaction.message)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="cfs", description="Gửi một confession ẩn danh")
    @app_commands.describe(attachment="(Tùy chọn) Đính kèm một tệp")
    async def confession(self, interaction: discord.Interaction, attachment: discord.Attachment = None):
        target_channel_id = await self.bot.db.get_setting(interaction.guild.id, 'cfs_channel_id')
        if not target_channel_id:
            return await interaction.response.send_message("Lỗi: Kênh confession chưa được thiết lập. Admin hãy dùng `/setchannel`.", ephemeral=True)
        target_channel = self.bot.get_channel(target_channel_id)
        if not target_channel:
            return await interaction.response.send_message("Lỗi: Không tìm thấy kênh confession đã thiết lập.", ephemeral=True)
        await interaction.response.send_modal(ConfessionModal(target_channel=target_channel, bot=self.bot, attachment=attachment))

async def setup(bot: commands.Bot):
    await bot.add_cog(ConfessionCog(bot))
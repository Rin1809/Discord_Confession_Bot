import discord
from discord import app_commands, ui
from discord.ext import commands

class MessageModal(ui.Modal):
    message_content = ui.TextInput(label='Nội dung', style=discord.TextStyle.long, max_length=2000)
    
    def __init__(self, title: str, placeholder: str, db_key: str, bot: commands.Bot):
        super().__init__(title=title)
        self.message_content.placeholder = placeholder
        self.db_key = db_key
        self.bot = bot
        
    async def on_submit(self, interaction: discord.Interaction):
        await self.bot.db.set_setting(interaction.guild.id, self.db_key, self.message_content.value)
        await interaction.response.send_message(f"✅ Đã cập nhật tin nhắn cho: `{self.db_key}`", ephemeral=True)

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Lỗi: Bạn không có quyền dùng lệnh này.", ephemeral=True)
        else:
            print(f"Loi lenh admin: {error}")
            await interaction.response.send_message(f"Lỗi không xác định: {error}", ephemeral=True)

    @app_commands.command(name="setchannel", description="Thiết lập kênh confession (Admin).")
    @app_commands.describe(channel="Kênh để nhận confession.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.set_setting(interaction.guild.id, 'cfs_channel_id', channel.id)
        await interaction.response.send_message(f"✅ Đã thiết lập kênh confession là {channel.mention}.", ephemeral=True)

    async def _toggle_setting(self, interaction: discord.Interaction, db_key: str, feature_name: str):
        current_status = await self.bot.db.get_setting(interaction.guild.id, db_key)
        new_status = not current_status
        await self.bot.db.set_setting(interaction.guild.id, db_key, int(new_status))
        await interaction.response.send_message(f"✅ Đã **{'BẬT' if new_status else 'TẮT'}** tính năng {feature_name}.", ephemeral=True)

    async def _set_channel_setting(self, interaction: discord.Interaction, channel: discord.TextChannel, db_key: str, feature_name: str):
        await self.bot.db.set_setting(interaction.guild.id, db_key, channel.id)
        await interaction.response.send_message(f"✅ Kênh {feature_name} được đặt thành {channel.mention}.", ephemeral=True)

    # Welcome
    welcome_group = app_commands.Group(name="welcome", description="Cài đặt chào mừng thành viên (Admin)", guild_only=True)
    
    @welcome_group.command(name="toggle", description="Bật/Tắt tính năng chào mừng.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_welcome(self, interaction: discord.Interaction): await self._toggle_setting(interaction, 'welcome_enabled', 'chào mừng')
    
    @welcome_group.command(name="setchannel", description="Chọn kênh chào mừng.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel): await self._set_channel_setting(interaction, channel, 'welcome_channel_id', 'chào mừng')
    
    @welcome_group.command(name="setmessage", description="Tùy chỉnh tin nhắn chào mừng.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_message(self, interaction: discord.Interaction):
        modal = MessageModal('Thiết lập tin nhắn chào mừng', 'VD: Chào mừng {user.mention}!', 'welcome_message', self.bot)
        await interaction.response.send_modal(modal)

    # Leave
    leave_group = app_commands.Group(name="leave", description="Cài đặt thông báo rời đi (Admin)", guild_only=True)
    
    @leave_group.command(name="toggle", description="Bật/Tắt thông báo rời đi.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_leave(self, interaction: discord.Interaction): await self._toggle_setting(interaction, 'leave_enabled', 'thông báo rời đi')
    
    @leave_group.command(name="setchannel", description="Chọn kênh thông báo rời đi.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_leave_channel(self, interaction: discord.Interaction, channel: discord.TextChannel): await self._set_channel_setting(interaction, channel, 'leave_channel_id', 'thông báo rời đi')
    
    @leave_group.command(name="setmessage", description="Tùy chỉnh tin nhắn rời đi.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_leave_message(self, interaction: discord.Interaction):
        modal = MessageModal('Thiết lập tin nhắn rời đi', 'VD: Tạm biệt {user.name}...', 'leave_message', self.bot)
        await interaction.response.send_modal(modal)
        
    # Boost
    boost_group = app_commands.Group(name="boost", description="Cài đặt thông báo boost (Admin)", guild_only=True)
    
    @boost_group.command(name="toggle", description="Bật/Tắt thông báo boost.")
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_boost(self, interaction: discord.Interaction): await self._toggle_setting(interaction, 'boost_enabled', 'thông báo boost')
    
    @boost_group.command(name="setchannel", description="Chọn kênh thông báo boost.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_boost_channel(self, interaction: discord.Interaction, channel: discord.TextChannel): await self._set_channel_setting(interaction, channel, 'boost_channel_id', 'thông báo boost')
    
    @boost_group.command(name="setmessage", description="Tùy chỉnh tin nhắn boost.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_boost_message(self, interaction: discord.Interaction):
        modal = MessageModal('Thiết lập tin nhắn boost', 'VD: {user.mention} vừa boost!', 'boost_message', self.bot)
        await interaction.response.send_modal(modal)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
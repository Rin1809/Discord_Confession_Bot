import discord
from discord.ext import commands

class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        activity = discord.Activity(name="/cfs để gửi confession", type=discord.ActivityType.watching)
        await self.bot.change_presence(activity=activity)
        print(f'Da dang nhap voi ten {self.bot.user}')
        print('Bot san sang!')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = await self.bot.db.get_all_settings(member.guild.id)
        if not settings.get("welcome_enabled") or not settings.get("welcome_channel_id"): return

        channel = member.guild.get_channel(settings["welcome_channel_id"])
        if not channel: return

        try:
            message_template = settings.get("welcome_message") or "Chào mừng {user.mention}!"
            if settings.get("welcome_rules_channel_id"):
                message_template = message_template.replace("{rules_channel}", f"<#{settings['welcome_rules_channel_id']}>")
            if settings.get("welcome_lead_role_id"):
                message_template = message_template.replace("{lead_role_mention}", f"<@&{settings['welcome_lead_role_id']}>")
            
            final_title = (settings.get("welcome_title") or "Chào mừng!").format(user=member, server=member.guild)
            final_message = message_template.format(user=member, server=member.guild)
            
            embed = discord.Embed(title=final_title, description=final_message, color=discord.Color(0xFFB6C1))
            if member.guild.icon: embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)
            if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
            if settings.get("welcome_image_url"): embed.set_image(url=settings.get("welcome_image_url"))
            
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Loi khi gui tin chao mung cho server {member.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await self.bot.db.get_all_settings(member.guild.id)
        if not settings.get("leave_enabled") or not settings.get("leave_channel_id"): return
        
        channel = member.guild.get_channel(settings["leave_channel_id"])
        if not channel: return
        
        try:
            final_title = (settings.get("leave_title") or "{user.display_name} đã rời đi").format(user=member, server=member.guild)
            final_message = (settings.get("leave_message") or "Tạm biệt bạn.").format(user=member, server=member.guild)
            
            embed = discord.Embed(title=final_title, description=final_message, color=discord.Color(0x99aab5))
            if member.guild.icon: embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)
            if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
            if settings.get("leave_image_url"): embed.set_image(url=settings.get("leave_image_url"))
            
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Loi khi gui tin roi di cho server {member.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.premium_since is None and after.premium_since is not None:
            settings = await self.bot.db.get_all_settings(after.guild.id)
            if not settings.get("boost_enabled") or not settings.get("boost_channel_id"): return
            
            channel = after.guild.get_channel(settings["boost_channel_id"])
            if not channel: return

            try:
                message = (settings.get("boost_message") or "Cảm ơn {user.mention} đã boost server!").format(user=after, server=after.guild)
                
                embed = discord.Embed(description=message, color=discord.Color.magenta())
                embed.set_author(name=f"{after.display_name} vừa boost server!", icon_url=after.guild.icon.url if after.guild.icon else None)
                embed.set_thumbnail(url=after.display_avatar.url)
                if settings.get("boost_image_url"): embed.set_image(url=settings.get("boost_image_url"))
                
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Loi khi gui tin boost cho server {after.guild.id}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
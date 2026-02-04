import discord
from discord import app_commands
from discord.ext import commands
from database import Database, QUEST_INFO, TIER_SYSTEM
import asyncio
from datetime import datetime

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="ranking", description="View the Spot Zero agent leaderboard")
    async def ranking(self, interaction: discord.Interaction):
        """랭킹 보드 표시 (Cyberpunk Hall of Fame 스타일)"""
        leaderboard = self.db.get_leaderboard(limit=10)
        
        if not leaderboard:
            await interaction.response.send_message("No leaderboard data available.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Spot Zero: Agent Leaderboard",
            description="> Top agents ranked by clearance level and mission completion.",
            color=0xFFD700  # Gold
        )
        
        # 서버 아이콘 또는 트로피 아이콘을 썸네일로
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        # Top 3 (Agents of Legend)
        top3_text = ""
        medals = ["🥇", "🥈", "🥉"]
        place_names = ["1st Place", "2nd Place", "3rd Place"]
        
        for idx in range(min(3, len(leaderboard))):
            entry = leaderboard[idx]
            user_id = entry['user_id']
            total_xp = entry['total_xp']
            tier = self.db.get_user_tier(total_xp)
            tier_info = TIER_SYSTEM[tier]
            
            try:
                user = await self.bot.fetch_user(user_id)
                username = user.display_name
            except:
                username = f"User {user_id}"
            
            top3_text += (
                f"> **{medals[idx]} {place_names[idx]}** | **{username}**\n"
                f"> `[{tier_info['name']}] • {total_xp:,} XP`\n\n"
            )
        
        if top3_text:
            embed.add_field(
                name="👑 Agents of Legend",
                value=top3_text,
                inline=False
            )
        
        # Ranks 4-10 (Rising Agents) - Code Block 스타일
        if len(leaderboard) > 3:
            code_block_text = ""
            for idx in range(3, min(10, len(leaderboard))):
                entry = leaderboard[idx]
                user_id = entry['user_id']
                total_xp = entry['total_xp']
                tier = self.db.get_user_tier(total_xp)
                tier_info = TIER_SYSTEM[tier]
                
                try:
                    user = await self.bot.fetch_user(user_id)
                    username = user.display_name.replace('`', '')  # Code block 내 특수문자 제거
                except:
                    username = f"User_{user_id}"
                
                rank_num = idx + 1
                code_block_text += f"#{rank_num:02d} | {total_xp:>6,} XP | {username}\n"
            
            if code_block_text:
                embed.add_field(
                    name="📡 Rising Agents",
                    value=f"```text\n{code_block_text}```",
                    inline=False
                )
        
        # 사용자 자신의 순위 (20위 밖이면 표시)
        user_in_top_10 = any(entry['user_id'] == interaction.user.id for entry in leaderboard[:10])
        
        if not user_in_top_10:
            all_users = self.db.get_leaderboard(limit=1000)
            user_rank = None
            user_xp = None
            
            for idx, entry in enumerate(all_users, 1):
                if entry['user_id'] == interaction.user.id:
                    user_rank = idx
                    user_xp = entry['total_xp']
                    break
            
            if user_rank:
                tier = self.db.get_user_tier(user_xp)
                tier_info = TIER_SYSTEM[tier]
                
                embed.add_field(
                    name="━━━━━━━━━━━━━━━━━━━━",
                    value=(
                        f"> **#{user_rank}** | **{interaction.user.display_name}**\n"
                        f"> `[{tier_info['name']}] • {user_xp:,} XP`"
                    ),
                    inline=False
                )
        
        embed.set_footer(text="Complete more missions to climb the ranks!")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="log", description="View your recent XP acquisition history")
    async def log(self, interaction: discord.Interaction):
        """XP 획득 이력 표시"""
        await interaction.response.defer(ephemeral=True, thinking=True)

        # psycopg2는 blocking이므로 thread로 분리
        try:
            user = await asyncio.to_thread(self.db.get_or_create_user, interaction.user.id)
            xp_logs = await asyncio.to_thread(self.db.get_xp_logs, interaction.user.id, 15)
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to load XP history. Please try again later.\n`{e}`",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title="📜 XP History Log",
            description="Here are your recent activities.",
            color=discord.Color.blue()
        )
        
        if not xp_logs:
            embed.description = "No records found. Complete quests to start earning XP!"
        else:
            log_text = ""
            for log_entry in xp_logs:
                # 타임스탬프 포맷팅
                created_at = log_entry['created_at']
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                formatted_time = created_at.strftime('%Y/%m/%d %H:%M')
                mission_name = log_entry['mission_name']
                xp_amount = log_entry['xp_amount']
                
                log_text += f"`[{formatted_time}]` **{mission_name}** (`+{xp_amount} XP`)\n"
            
            embed.description = log_text
        
        # Footer에 총 XP 표시
        total_xp = user['total_xp']
        embed.set_footer(text=f"Total XP: {total_xp:,}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))

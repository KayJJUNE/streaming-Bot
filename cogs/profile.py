import discord
from discord import app_commands
from discord.ext import commands
from database import Database, QUEST_INFO, TIER_SYSTEM

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="ranking", description="랭킹 보드 확인")
    async def ranking(self, interaction: discord.Interaction):
        """랭킹 보드 표시 (20위까지, 자신이 밖이면 하단 표시)"""
        leaderboard = self.db.get_leaderboard(limit=20)
        
        if not leaderboard:
            await interaction.response.send_message("리더보드에 데이터가 없습니다.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Spot Zero 랭킹 보드",
            description="상위 20명의 사용자",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        # 사용자 순위 찾기
        user_rank = None
        user_xp = None
        user_in_top_20 = False
        
        for idx, entry in enumerate(leaderboard, 1):
            user_id = entry['user_id']
            total_xp = entry['total_xp']
            tier = self.db.get_user_tier(total_xp)
            tier_info = TIER_SYSTEM[tier]
            
            try:
                user = await self.bot.fetch_user(user_id)
                username = user.display_name
            except:
                username = f"User {user_id}"
            
            medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
            
            leaderboard_text += (
                f"{medal} {username} - **{tier_info['name']}** "
                f"(Lv.{tier}) - {total_xp:,} XP\n"
            )
            
            # 자신의 순위 확인
            if user_id == interaction.user.id:
                user_rank = idx
                user_xp = total_xp
                user_in_top_20 = True
        
        embed.description = leaderboard_text
        
        # 자신이 20위 안에 없으면 전체 순위 찾기
        if not user_in_top_20:
            all_users = self.db.get_leaderboard(limit=1000)  # 충분히 큰 수
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
                        f"**{user_rank}.** {interaction.user.display_name} - "
                        f"**{tier_info['name']}** (Lv.{tier}) - {user_xp:,} XP"
                    ),
                    inline=False
                )
        
        embed.set_footer(text="더 많은 XP를 획득하여 상위권에 도전하세요!")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))

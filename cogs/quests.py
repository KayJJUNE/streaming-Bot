import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, Select, View
from database import Database, QUEST_INFO, TIER_SYSTEM
import os

class QuestsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="sz", description="퀘스트 보드 및 제출")
    async def sz(self, interaction: discord.Interaction):
        """퀘스트 보드 표시 및 제출 모달"""
        user = self.db.get_or_create_user(interaction.user.id)
        
        # 반려된 제출 확인
        rejected_submissions = self.db.get_rejected_submissions(interaction.user.id)
        
        embed = discord.Embed(
            title="🎮 Spot Zero 퀘스트 보드",
            description="아래 퀘스트를 완료하여 XP를 획득하고 티어를 올리세요!",
            color=discord.Color.gold()
        )
        
        # 직접 제출 퀘스트
        direct_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] in ['one-time', 'repeatable']:
                status = "✅ 완료" if self.db.is_quest_completed(interaction.user.id, code) else "⏳ 미완료"
                if info['type'] == 'repeatable':
                    count = self.db.get_approved_count(interaction.user.id, code)
                    status = f"✅ {count}회 완료 (반복 가능)"
                
                direct_quests.append(
                    f"**{code}: {info['name']}** - {info['xp']} XP\n"
                    f"상태: {status}"
                )
        
        embed.add_field(
            name="📝 직접 제출 퀘스트",
            value="\n\n".join(direct_quests) if direct_quests else "없음",
            inline=False
        )
        
        # 마일스톤 퀘스트
        milestone_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] == 'milestone':
                is_completed = self.db.is_quest_completed(interaction.user.id, code)
                status = "✅ 완료" if is_completed else "⏳ 진행 중"
                
                # 진행도 표시
                if code == 'D':
                    count = self.db.get_approved_count(interaction.user.id, 'B')
                    progress = f"({count}/5)"
                elif code == 'E':
                    count = self.db.get_approved_count(interaction.user.id, 'B')
                    progress = f"({count}/10)"
                elif code == 'F':
                    count = self.db.get_approved_count(interaction.user.id, 'C')
                    progress = f"({count}/3)"
                elif code == 'G':
                    count = self.db.get_approved_count(interaction.user.id, 'C')
                    progress = f"({count}/6)"
                else:
                    progress = ""
                
                milestone_quests.append(
                    f"**{code}: {info['name']}** - {info['xp']} XP {progress}\n"
                    f"상태: {status}"
                )
        
        embed.add_field(
            name="🎯 마일스톤 퀘스트 (자동 완료)",
            value="\n\n".join(milestone_quests) if milestone_quests else "없음",
            inline=False
        )
        
        # 현재 티어 정보
        total_xp = user['total_xp']
        current_tier = self.db.get_user_tier(total_xp)
        tier_info = TIER_SYSTEM[current_tier]
        
        next_tier = None
        for tier_level, info in sorted(TIER_SYSTEM.items()):
            if info['xp_required'] > total_xp:
                next_tier = (tier_level, info)
                break
        
        tier_text = f"**{tier_info['name']}** (Lv.{current_tier})"
        if next_tier:
            tier_text += f"\n다음 티어: {next_tier[1]['name']} (Lv.{next_tier[0]}) - {next_tier[1]['xp_required'] - total_xp} XP 필요"
        
        embed.add_field(
            name="🏆 현재 티어",
            value=tier_text,
            inline=False
        )
        
        # 반려된 제출이 있으면 표시
        if rejected_submissions:
            rejected_text = ""
            for sub in rejected_submissions[:5]:  # 최근 5개만 표시
                quest_name = QUEST_INFO.get(sub['mission_code'], {}).get('name', sub['mission_code'])
                reason = sub.get('rejection_reason', '사유 없음')
                rejected_text += f"**{quest_name}** ({sub['mission_code']}): {reason}\n"
            
            embed.add_field(
                name="❌ 반려된 제출",
                value=rejected_text if rejected_text else "없음",
                inline=False
            )
        
        embed.set_footer(text=f"총 XP: {total_xp}")
        
        # 제출 버튼 추가
        view = QuestSubmissionView(self.db, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class QuestSubmissionView(View):
    def __init__(self, db: Database, bot: commands.Bot):
        super().__init__(timeout=None)
        self.db = db
        self.bot = bot
    
    @discord.ui.button(label="퀘스트 제출", style=discord.ButtonStyle.primary, custom_id="submit_quest")
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """퀘스트 제출 모달 열기"""
        # 제출 가능한 퀘스트 목록 생성
        available_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] in ['one-time', 'repeatable']:
                # 원타임 퀘스트는 완료하지 않은 것만
                if info['type'] == 'one-time':
                    if not self.db.is_quest_completed(interaction.user.id, code):
                        available_quests.append((code, info))
                else:
                    # 반복 가능한 퀘스트는 항상 제출 가능
                    available_quests.append((code, info))
        
        if not available_quests:
            await interaction.response.send_message(
                "❌ 제출 가능한 퀘스트가 없습니다.",
                ephemeral=True
            )
            return
        
        # 모달 표시
        modal = QuestSubmissionModal(available_quests, self.db, self.bot)
        await interaction.response.send_modal(modal)


class QuestSubmissionModal(Modal, title="퀘스트 제출"):
    def __init__(self, available_quests, db: Database, bot: commands.Bot):
        super().__init__()
        self.db = db
        self.bot = bot
        
        # 퀘스트 선택 드롭다운
        self.quest_select = Select(
            placeholder="제출할 퀘스트를 선택하세요",
            options=[
                discord.SelectOption(
                    label=f"{code}: {info['name']} ({info['xp']} XP)",
                    value=code,
                    description=f"{info['type']} - {info['xp']} XP"
                )
                for code, info in available_quests
            ]
        )
        self.add_item(self.quest_select)
        
        # 링크 입력 필드
        self.link_input = discord.ui.TextInput(
            label="링크/증거",
            placeholder="제출할 링크 또는 증거를 입력하세요",
            required=True,
            max_length=1000
        )
        self.add_item(self.link_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 처리"""
        mission_code = self.quest_select.values[0] if self.quest_select.values else None
        link = self.link_input.value
        
        if not mission_code:
            await interaction.response.send_message(
                "❌ 퀘스트를 선택해주세요.",
                ephemeral=True
            )
            return
        
        mission_code = mission_code.upper()
        quest_info = QUEST_INFO.get(mission_code)
        
        if not quest_info:
            await interaction.response.send_message(
                "❌ 유효하지 않은 미션 코드입니다.",
                ephemeral=True
            )
            return
        
        # 원타임 퀘스트 중복 체크
        if quest_info['type'] == 'one-time':
            if self.db.is_quest_completed(interaction.user.id, mission_code):
                await interaction.response.send_message(
                    f"❌ {quest_info['name']}은(는) 이미 완료한 원타임 퀘스트입니다.",
                    ephemeral=True
                )
                return
        
        # 제출 생성
        submission_id = self.db.create_submission(
            interaction.user.id,
            mission_code,
            link
        )
        
        # 관리자 승인 채널로 전송
        admin_channel_id = int(os.getenv('ADMIN_CHANNEL_ID', '0'))
        if admin_channel_id:
            admin_channel = self.bot.get_channel(admin_channel_id)
            if admin_channel:
                embed = discord.Embed(
                    title="새로운 퀘스트 제출",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="사용자", value=f"<@{interaction.user.id}>", inline=True)
                embed.add_field(name="미션", value=f"{mission_code}: {quest_info['name']}", inline=True)
                embed.add_field(name="보상", value=f"{quest_info['xp']} XP", inline=True)
                embed.add_field(name="링크/증거", value=link, inline=False)
                embed.add_field(name="제출 ID", value=f"#{submission_id}", inline=False)
                embed.set_footer(text=f"User ID: {interaction.user.id}")
                
                view = ApprovalView(submission_id, self.db, self.bot)
                await admin_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ **{quest_info['name']}** 제출이 완료되었습니다!\n"
            f"24시간 내 확인할 수 있습니다.",
            ephemeral=True
        )


class ApprovalView(discord.ui.View):
    def __init__(self, submission_id: int, db: Database, bot: commands.Bot):
        super().__init__(timeout=None)
        self.submission_id = submission_id
        self.db = db
        self.bot = bot
    
    @discord.ui.button(label="✅ 승인", style=discord.ButtonStyle.green, custom_id="approve_btn")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 관리자만 승인할 수 있습니다.", ephemeral=True)
            return
        
        success, message, milestone_rewards = self.db.approve_submission(self.submission_id)
        
        if success:
            submission = self.db.get_submission(self.submission_id)
            user_id = submission['user_id']
            mission_code = submission['mission_code']
            quest_info = QUEST_INFO[mission_code]
            
            # 사용자에게 DM 전송
            try:
                user = await self.bot.fetch_user(user_id)
                dm_embed = discord.Embed(
                    title="✅ 퀘스트 승인됨!",
                    description=f"**{quest_info['name']}**이(가) 승인되었습니다!",
                    color=discord.Color.green()
                )
                dm_embed.add_field(name="획득 XP", value=f"{quest_info['xp']} XP", inline=True)
                
                # 마일스톤 보상이 있다면 추가
                if milestone_rewards:
                    milestone_text = "\n".join([
                        f"🎯 {QUEST_INFO[r['mission']]['name']}: +{r['xp']} XP"
                        for r in milestone_rewards
                    ])
                    dm_embed.add_field(
                        name="마일스톤 달성!",
                        value=milestone_text,
                        inline=False
                    )
                
                await user.send(embed=dm_embed)
            except:
                pass  # DM 전송 실패 시 무시
            
            # 역할 업데이트
            await self._update_user_roles(user_id, interaction.guild)
            
            # 승인 메시지 업데이트
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="승인 상태", value=f"✅ 승인됨 by {interaction.user.mention}", inline=False)
            
            if milestone_rewards:
                milestone_text = "\n".join([
                    f"🎯 {QUEST_INFO[r['mission']]['name']}: +{r['xp']} XP"
                    for r in milestone_rewards
                ])
                embed.add_field(name="마일스톤 달성", value=milestone_text, inline=False)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
    
    @discord.ui.button(label="❌ 거부", style=discord.ButtonStyle.red, custom_id="reject_btn")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 관리자만 거부할 수 있습니다.", ephemeral=True)
            return
        
        # 반려 사유 입력 모달 표시
        modal = RejectionReasonModal(self.submission_id, self.db, self.bot)
        await interaction.response.send_modal(modal)
    
    async def _update_user_roles(self, user_id: int, guild: discord.Guild):
        """사용자 역할 업데이트"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        total_xp = user['total_xp']
        current_tier = self.db.get_user_tier(total_xp)
        
        # 모든 티어 역할 찾기
        tier_roles = {}
        for tier_level, tier_info in TIER_SYSTEM.items():
            role = discord.utils.get(guild.roles, name=tier_info['role_name'])
            if role:
                tier_roles[tier_level] = role
        
        # 현재 티어 이하의 모든 역할 부여
        roles_to_add = []
        for tier_level in range(1, current_tier + 1):
            if tier_level in tier_roles:
                roles_to_add.append(tier_roles[tier_level])
        
        # 역할 추가 (없는 것만)
        for role in roles_to_add:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"티어 업그레이드: Lv.{current_tier}")
                except:
                    pass
        
        # 현재 티어보다 높은 역할 제거
        for tier_level in range(current_tier + 1, 6):
            if tier_level in tier_roles:
                role = tier_roles[tier_level]
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason=f"티어 다운그레이드")
                    except:
                        pass


class RejectionReasonModal(Modal, title="반려 사유 작성"):
    def __init__(self, submission_id: int, db: Database, bot: commands.Bot):
        super().__init__()
        self.submission_id = submission_id
        self.db = db
        self.bot = bot
        
        self.reason_input = discord.ui.TextInput(
            label="반려 사유",
            placeholder="반려 사유를 입력하세요",
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """반려 사유 제출 처리"""
        reason = self.reason_input.value
        
        # 반려 처리
        self.db.reject_submission(self.submission_id, reason)
        
        submission = self.db.get_submission(self.submission_id)
        user_id = submission['user_id']
        mission_code = submission['mission_code']
        quest_info = QUEST_INFO.get(mission_code, {})
        quest_name = quest_info.get('name', mission_code)
        
        # 사용자에게 DM 전송
        try:
            user = await self.bot.fetch_user(user_id)
            dm_embed = discord.Embed(
                title="❌ 퀘스트 반려됨",
                description=f"**{quest_name}** 제출이 반려되었습니다.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="반려 사유", value=reason, inline=False)
            dm_embed.add_field(
                name="재제출",
                value="`/sz` 명령어를 사용하여 다시 제출할 수 있습니다.",
                inline=False
            )
            await user.send(embed=dm_embed)
        except:
            pass
        
        # 반려 메시지 업데이트
        original_embed = None
        async for message in interaction.channel.history(limit=10):
            if message.embeds and message.embeds[0].fields:
                for field in message.embeds[0].fields:
                    if field.name == "제출 ID" and f"#{self.submission_id}" in field.value:
                        original_embed = message.embeds[0]
                        break
            if original_embed:
                break
        
        if original_embed:
            original_embed.color = discord.Color.red()
            original_embed.add_field(name="승인 상태", value=f"❌ 거부됨 by {interaction.user.mention}", inline=False)
            original_embed.add_field(name="반려 사유", value=reason, inline=False)
            
            # 원본 메시지 찾아서 업데이트
            async for message in interaction.channel.history(limit=10):
                if message.embeds and len(message.embeds) > 0:
                    if message.embeds[0].title == "새로운 퀘스트 제출":
                        for field in message.embeds[0].fields:
                            if field.name == "제출 ID" and f"#{self.submission_id}" in field.value:
                                await message.edit(embed=original_embed, view=None)
                                break
        
        await interaction.response.send_message(
            f"✅ 반려 처리 완료. 반려 사유가 사용자에게 전송되었습니다.",
            ephemeral=True
        )
    
    async def _update_user_roles(self, user_id: int, guild: discord.Guild):
        """사용자 역할 업데이트"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        total_xp = user['total_xp']
        current_tier = self.db.get_user_tier(total_xp)
        
        # 모든 티어 역할 찾기
        tier_roles = {}
        for tier_level, tier_info in TIER_SYSTEM.items():
            role = discord.utils.get(guild.roles, name=tier_info['role_name'])
            if role:
                tier_roles[tier_level] = role
        
        # 현재 티어 이하의 모든 역할 부여
        roles_to_add = []
        for tier_level in range(1, current_tier + 1):
            if tier_level in tier_roles:
                roles_to_add.append(tier_roles[tier_level])
        
        # 역할 추가 (없는 것만)
        for role in roles_to_add:
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"티어 업그레이드: Lv.{current_tier}")
                except:
                    pass
        
        # 현재 티어보다 높은 역할 제거
        for tier_level in range(current_tier + 1, 6):
            if tier_level in tier_roles:
                role = tier_roles[tier_level]
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason=f"티어 다운그레이드")
                    except:
                        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(QuestsCog(bot))

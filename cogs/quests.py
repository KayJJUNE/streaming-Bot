import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, Select, View
from database import Database, QUEST_INFO, TIER_SYSTEM
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

def draw_progress_bar(current_xp: int, target_xp: int, bar_length: int = 10) -> str:
    """XP 진행 바를 생성하는 헬퍼 함수"""
    if target_xp <= 0:
        return f"[{'█' * bar_length}] 100%"
    
    percentage = min(current_xp / target_xp, 1.0) if target_xp > 0 else 1.0
    filled = int(percentage * bar_length)
    empty = bar_length - filled
    
    bar = "█" * filled + "░" * empty
    percentage_text = int(percentage * 100)
    
    return f"[{bar}] {percentage_text}%"

class QuestsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="sz", description="Open your Agent Status Board and submit quest proof")
    async def sz(self, interaction: discord.Interaction):
        """퀘스트 보드 표시 및 제출 모달 (Sci-Fi RPG 스타일). DB 조회는 스레드에서 수행해 이벤트 루프 블로킹 방지."""
        await interaction.response.defer(ephemeral=True)

        try:
            data = await asyncio.to_thread(self.db.get_quest_board_data, interaction.user.id)
        except Exception as e:
            logger.error(
                "sz 보드 데이터 조회 실패 user_id=%s error=%s",
                interaction.user.id,
                e,
                exc_info=True,
            )
            await interaction.followup.send(
                "❌ 보드를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                ephemeral=True,
            )
            return

        user = data['user']
        # rejected_submissions는 보드에 표시하지 않지만 추후 확장용으로 반환됨

        # Sci-Fi RPG 스타일 임베드
        embed = discord.Embed(
            title="🛡️ Spot Zero: Agent Status Board",
            description="> Welcome, Agent. Complete missions to increase your clearance level.",
            color=0x00F0FF  # Neon Blue
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        total_xp = user['total_xp']
        current_tier = self.db.get_user_tier(total_xp)
        tier_info = TIER_SYSTEM[current_tier]

        next_tier = None
        for tier_level, info in sorted(TIER_SYSTEM.items()):
            if info['xp_required'] > total_xp:
                next_tier = (tier_level, info)
                break

        if next_tier:
            target_xp = next_tier[1]['xp_required']
            current_progress = total_xp - tier_info['xp_required']
            progress_needed = target_xp - tier_info['xp_required']
            progress_bar = draw_progress_bar(current_progress, progress_needed)
            xp_to_next = target_xp - total_xp
        else:
            progress_bar = draw_progress_bar(1, 1)
            xp_to_next = 0

        tier_emojis = {1: "🥉", 2: "🥈", 3: "🥇", 4: "💎", 5: "👑"}
        tier_emoji = tier_emojis.get(current_tier, "⭐")

        profile_text = f"{tier_emoji} **Current Rank:** {tier_info['name']} (Lv.{current_tier})\n"
        profile_text += f"📊 **Total XP:** {total_xp:,}\n"
        profile_text += f"📈 **Progress:** {progress_bar}\n"
        if next_tier and xp_to_next > 0:
            profile_text += f"🎯 **Next Tier Goal:** {xp_to_next:,} XP to {next_tier[1]['name']}"
        else:
            profile_text += f"🏆 **Status:** Maximum Rank Achieved!"
        embed.add_field(name="👤 User Profile", value=profile_text, inline=False)

        one_time_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] != 'one-time':
                continue
            is_completed = data['one_time'].get(code, False)
            status_emoji = "✅" if is_completed else "⬜"
            status_text = "Completed" if is_completed else "Not Started"
            lines = [
                f"> **[ Mission {code} ]** {info['name']}\n",
                f"> `Reward: {info['xp']} XP` | `Status: {status_emoji} {status_text}`",
            ]
            if info.get('video_url'):
                lines.insert(1, f"> 🔗 {info['video_url']}\n")
            if info.get('short_description'):
                lines.insert(2 if info.get('video_url') else 1, f"> *{info['short_description']}*\n")
            one_time_quests.append("".join(lines))

        repeatable_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] != 'repeatable':
                continue
            count = data['repeatable'].get(code, 0)
            repeatable_quests.append(
                f"> **[ Mission {code} ]** {info['name']}\n"
                f"> `Reward: {info['xp']} XP` | `Status: 🔄 Repeatable ({count} completed)`"
            )

        missions_text = ""
        if one_time_quests:
            missions_text += "**⚔️ One-Time Missions:**\n" + "\n".join(one_time_quests) + "\n\n"
        if repeatable_quests:
            missions_text += "**🔄 Repeatable Missions:**\n" + "\n".join(repeatable_quests) + "\n\n"
        if not missions_text:
            missions_text = "> No active missions available."
        embed.add_field(name="📜 Active Missions", value=missions_text, inline=False)

        milestone_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] != 'milestone':
                continue
            m = data['milestone'].get(code, {})
            is_completed = m.get('completed', False)
            status_emoji = "✅" if is_completed else "📡"
            status_text = "Completed" if is_completed else "In Progress"
            if code == 'D':
                progress = f"({m.get('count_b', 0)}/5)"
            elif code == 'E':
                progress = f"({m.get('count_b', 0)}/10)"
            elif code == 'F':
                progress = f"({m.get('count_c', 0)}/3)"
            elif code == 'G':
                progress = f"({m.get('count_c', 0)}/6)"
            else:
                progress = ""
            milestone_quests.append(
                f"> **[ Mission {code} ]** {info['name']} {progress}\n"
                f"> `Reward: {info['xp']} XP` | `Status: {status_emoji} {status_text}`"
            )

        if milestone_quests:
            milestone_text = "**🎁 Milestone Rewards (Auto-complete):**\n" + "\n".join(milestone_quests)
            embed.add_field(name="🎯 Milestone Quests", value=milestone_text, inline=False)

        guild_icon = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None
        embed.set_footer(text="Select a mission below to submit proof.", icon_url=guild_icon)

        view = QuestSelectView(interaction.user.id, self.db, self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class QuestSelectView(View):
    """퀘스트 선택 드롭다운 메뉴가 포함된 View"""
    def __init__(self, user_id: int, db: Database, bot: commands.Bot):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.user_id = user_id
        self.db = db
        self.bot = bot
        
        # 제출 가능한 퀘스트 목록 생성
        available_quests = []
        for code, info in QUEST_INFO.items():
            if info['type'] in ['one-time', 'repeatable']:
                # 원타임 퀘스트는 완료하지 않은 것만
                if info['type'] == 'one-time':
                    if not self.db.is_quest_completed(user_id, code):
                        available_quests.append((code, info))
                else:
                    # 반복 가능한 퀘스트는 항상 제출 가능
                    available_quests.append((code, info))
        
        # 드롭다운 메뉴 생성
        if available_quests:
            select_options = []
            for code, info in available_quests:
                # 드롭다운 옵션 레이블 생성
                if code == 'A':
                    label = "Mission A: Promo Video"
                elif code == 'B':
                    label = "Mission B: Upload Video"
                elif code == 'C':
                    label = "Mission C: Live Stream"
                elif code == 'H':
                    label = "Mission H: High Engagement"
                else:
                    label = f"{code}: {info['name']}"
                
                select_options.append(
                    discord.SelectOption(
                        label=label,
                        value=code,
                        description=f"{info['xp']} XP - {info['type']}"
                    )
                )
            
            self.quest_select = QuestSelect(
                placeholder="제출할 퀘스트를 선택하세요",
                options=select_options,
                db=self.db,
                bot=self.bot
            )
            self.add_item(self.quest_select)
    
    async def on_timeout(self):
        """View 타임아웃 시 처리"""
        # 타임아웃 시 아무 작업도 하지 않음 (뷰가 비활성화됨)
        pass


class QuestSelect(Select):
    """퀘스트 선택 드롭다운"""
    def __init__(self, placeholder: str, options: list, db: Database, bot: commands.Bot):
        super().__init__(placeholder=placeholder, options=options, min_values=1, max_values=1)
        self.db = db
        self.bot = bot
    
    async def callback(self, interaction: discord.Interaction):
        """드롭다운에서 퀘스트 선택 시 모달 열기"""
        selected_code = self.values[0]
        quest_info = QUEST_INFO.get(selected_code)
        
        if not quest_info:
            await interaction.response.send_message(
                "❌ 유효하지 않은 미션 코드입니다.",
                ephemeral=True
            )
            return
        
        # 원타임 퀘스트 중복 체크
        if quest_info['type'] == 'one-time':
            if self.db.is_quest_completed(interaction.user.id, selected_code):
                await interaction.response.send_message(
                    f"❌ {quest_info['name']}은(는) 이미 완료한 원타임 퀘스트입니다.",
                    ephemeral=True
                )
                return
        
        # 모달 열기
        modal = SubmissionModal(selected_code, quest_info, self.db, self.bot)
        await interaction.response.send_modal(modal)


class SubmissionModal(Modal):
    """퀘스트 제출 모달"""
    def __init__(self, mission_code: str, quest_info: dict, db: Database, bot: commands.Bot):
        # 모달 제목 설정
        quest_name = quest_info['name']
        if mission_code == 'A':
            title = "Submit Mission A"
        elif mission_code == 'B':
            title = "Submit Mission B"
        elif mission_code == 'C':
            title = "Submit Mission C"
        elif mission_code == 'H':
            title = "Submit Mission H"
        else:
            title = f"Submit {mission_code}: {quest_name}"
        
        super().__init__(title=title)
        self.mission_code = mission_code
        self.quest_info = quest_info
        self.db = db
        self.bot = bot
        
        # 링크 입력 필드
        self.link_input = discord.ui.TextInput(
            label="Proof URL / Link",
            placeholder="제출할 링크 또는 증거를 입력하세요",
            required=True,
            max_length=1000,
            style=discord.TextStyle.short
        )
        self.add_item(self.link_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 처리"""
        try:
            link = self.link_input.value.strip()
            
            if not link:
                await interaction.response.send_message(
                    "❌ 링크를 입력해주세요.",
                    ephemeral=True
                )
                return
            
            # 원타임 퀘스트 중복 체크 (한 번 더 확인)
            if self.quest_info['type'] == 'one-time':
                if self.db.is_quest_completed(interaction.user.id, self.mission_code):
                    await interaction.response.send_message(
                        f"❌ {self.quest_info['name']}은(는) 이미 완료한 원타임 퀘스트입니다.",
                        ephemeral=True
                    )
                    return
            
            # 제출 생성
            try:
                submission_id = self.db.create_submission(
                    interaction.user.id,
                    self.mission_code,
                    link
                )
            except Exception as e:
                logger.error(
                    "퀘스트 제출 생성 실패 user_id=%s mission_code=%s error=%s",
                    interaction.user.id,
                    self.mission_code,
                    e,
                    exc_info=True,
                )
                await interaction.response.send_message(
                    "❌ 제출 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    ephemeral=True
                )
                return
            
            # 사용자에게 먼저 응답 (3초 이내 응답 필요)
            await interaction.response.send_message(
                "✅ **Submission received!** Admins will review it soon.",
                ephemeral=True
            )
            
            # 관리자 승인 채널로 전송 (응답 후 비동기로 처리)
            try:
                admin_channel_id_str = os.getenv('ADMIN_CHANNEL_ID', '0')
                if not admin_channel_id_str or admin_channel_id_str == 'your_channel_id_here':
                    logger.warning("ADMIN_CHANNEL_ID가 설정되지 않음. 제출 user_id=%s", interaction.user.id)
                    # 관리자 채널이 없어도 제출은 성공했으므로 사용자에게는 성공 메시지 표시
                    return
                
                admin_channel_id = int(admin_channel_id_str)
                admin_channel = self.bot.get_channel(admin_channel_id)
                
                if not admin_channel:
                    logger.warning(
                        "관리자 채널을 찾을 수 없음 channel_id=%s 제출 user_id=%s",
                        admin_channel_id,
                        interaction.user.id,
                    )
                    # 채널을 찾지 못해도 제출은 성공했으므로 계속 진행
                    return
                
                # Ticket 스타일 임베드 생성
                embed = discord.Embed(
                    title="🚨 New Quest Submission",
                    color=discord.Color.orange(),  # Orange (Pending state)
                    timestamp=discord.utils.utcnow()
                )
                
                # 사용자 정보 (클릭 가능한 멘션)
                user_mention = f"<@{interaction.user.id}>"
                embed.add_field(
                    name="👤 User",
                    value=f"{user_mention}\nID: `{interaction.user.id}`",
                    inline=True
                )
                
                # 미션 정보
                mission_label = f"Mission {self.mission_code}"
                embed.add_field(
                    name="🎯 Mission",
                    value=f"**{mission_label}**\n{self.quest_info['name']}\n**Reward:** {self.quest_info['xp']} XP",
                    inline=True
                )
                
                # 증거 링크 (강조)
                embed.add_field(
                    name="🔗 Proof",
                    value=f"[Click here]({link})\n`{link}`",
                    inline=False
                )
                
                # 제출 ID
                embed.add_field(
                    name="📋 Submission ID",
                    value=f"`#{submission_id}`",
                    inline=True
                )
                
                embed.set_footer(text="Pending Review • Click a button below to process")
                
                view = AdminApprovalView(submission_id, self.db, self.bot)
                await admin_channel.send(embed=embed, view=view)
                
            except ValueError:
                logger.warning(
                    "ADMIN_CHANNEL_ID 유효하지 않음 value=%s user_id=%s",
                    admin_channel_id_str,
                    interaction.user.id,
                )
            except Exception as e:
                logger.error(
                    "관리자 채널 전송 실패 user_id=%s submission_id=%s error=%s",
                    interaction.user.id,
                    submission_id,
                    e,
                    exc_info=True,
                )
                # 관리자 채널 전송 실패해도 제출은 성공했으므로 사용자에게는 성공 메시지 표시
        
        except Exception as e:
            logger.exception(
                "모달 제출 처리 중 예상치 못한 오류 user_id=%s mission_code=%s error=%s",
                interaction.user.id,
                getattr(self, "mission_code", None),
                e,
            )

            # 이미 응답을 보냈는지 확인
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        "❌ 제출 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                        ephemeral=True
                    )
                except:
                    # 응답 실패 시 followup 사용
                    await interaction.followup.send(
                        "❌ 제출 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                        ephemeral=True
                    )


class AdminApprovalView(discord.ui.View):
    """관리자 승인/거부 버튼이 있는 View (Persistent)"""
    def __init__(self, submission_id: int, db: Database, bot: commands.Bot):
        super().__init__(timeout=None)  # Persistent View
        self.submission_id = submission_id
        self.db = db
        self.bot = bot
    
    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green, custom_id="approve_btn")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """승인 버튼 처리"""
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 관리자만 승인할 수 있습니다.",
                ephemeral=True
            )
            return
        
        # 응답 지연 (데이터베이스 작업 시간 확보)
        await interaction.response.defer()
        
        try:
            # 데이터베이스에서 승인 처리
            success, message, milestone_rewards = self.db.approve_submission(self.submission_id)
            
            if not success:
                await interaction.followup.send(
                    f"❌ 승인 처리 실패: {message}",
                    ephemeral=True
                )
                return
            
            # 제출 정보 조회
            submission = self.db.get_submission(self.submission_id)
            if not submission:
                await interaction.followup.send(
                    "❌ 제출 정보를 찾을 수 없습니다.",
                    ephemeral=True
                )
                return
            
            user_id = submission['user_id']
            mission_code = submission['mission_code']
            quest_info = QUEST_INFO.get(mission_code)
            
            if not quest_info:
                await interaction.followup.send(
                    "❌ 유효하지 않은 미션 코드입니다.",
                    ephemeral=True
                )
                return
            
            # 원본 임베드 가져오기
            original_embed = interaction.message.embeds[0]
            
            # 승인된 임베드 생성
            approved_embed = discord.Embed(
                title="✅ Submission Approved",
                color=0x00FF00,  # Green
                timestamp=original_embed.timestamp
            )
            
            # 원본 필드 복사 및 수정
            for field in original_embed.fields:
                approved_embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )
            
            # 마일스톤 보상이 있다면 추가
            if milestone_rewards:
                milestone_text = "\n".join([
                    f"🎯 **{QUEST_INFO[r['mission']]['name']}**: +{r['xp']} XP"
                    for r in milestone_rewards
                ])
                approved_embed.add_field(
                    name="🎉 Milestone Achieved!",
                    value=milestone_text,
                    inline=False
                )
            
            # Footer에 승인자 정보 추가
            approved_embed.set_footer(text=f"Approved by {interaction.user.display_name}")
            
            # 버튼 비활성화된 View 생성
            disabled_view = discord.ui.View()
            disabled_view.add_item(
                discord.ui.Button(
                    label="✅ Approved",
                    style=discord.ButtonStyle.green,
                    disabled=True
                )
            )
            disabled_view.add_item(
                discord.ui.Button(
                    label="❌ Reject",
                    style=discord.ButtonStyle.red,
                    disabled=True
                )
            )
            
            # 메시지 수정
            await interaction.message.edit(embed=approved_embed, view=disabled_view)
            
            # 사용자에게 DM 전송
            try:
                user = await self.bot.fetch_user(user_id)
                dm_embed = discord.Embed(
                    title="🎉 Submission Approved!",
                    description=f"Your submission for **{quest_info['name']}** has been approved!",
                    color=discord.Color.green()
                )
                dm_embed.add_field(
                    name="XP Earned",
                    value=f"+{quest_info['xp']} XP",
                    inline=True
                )
                
                # 마일스톤 보상이 있다면 추가
                if milestone_rewards:
                    total_milestone_xp = sum(r['xp'] for r in milestone_rewards)
                    milestone_text = "\n".join([
                        f"🎯 {QUEST_INFO[r['mission']]['name']}: +{r['xp']} XP"
                        for r in milestone_rewards
                    ])
                    dm_embed.add_field(
                        name="🎉 Milestone Achieved!",
                        value=f"{milestone_text}\n\n**Total Bonus:** +{total_milestone_xp} XP",
                        inline=False
                    )
                
                await user.send(embed=dm_embed)
            except Exception as e:
                logger.error(
                    "승인 알림 DM 전송 실패 user_id=%s submission_id=%s error=%s",
                    user_id,
                    self.submission_id,
                    e,
                    exc_info=True,
                )

            # 역할 업데이트
            if interaction.guild:
                await self._update_user_roles(user_id, interaction.guild)
            
            # 성공 메시지
            await interaction.followup.send(
                "✅ Submission approved successfully!",
                ephemeral=True
            )
            
        except Exception as e:
            logger.exception(
                "승인 처리 중 오류 submission_id=%s admin_id=%s error=%s",
                self.submission_id,
                interaction.user.id,
                e,
            )
            await interaction.followup.send(
                f"❌ 승인 처리 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.red, custom_id="reject_btn")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """거부 버튼 처리"""
        # 관리자 권한 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 관리자만 거부할 수 있습니다.",
                ephemeral=True
            )
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
        reason = self.reason_input.value.strip()
        
        if not reason:
            await interaction.response.send_message(
                "❌ 반려 사유를 입력해주세요.",
                ephemeral=True
            )
            return
        
        # 응답 지연
        await interaction.response.defer()
        
        try:
            # 반려 처리
            self.db.reject_submission(self.submission_id, reason)
            
            submission = self.db.get_submission(self.submission_id)
            if not submission:
                await interaction.followup.send(
                    "❌ 제출 정보를 찾을 수 없습니다.",
                    ephemeral=True
                )
                return
            
            user_id = submission['user_id']
            mission_code = submission['mission_code']
            quest_info = QUEST_INFO.get(mission_code, {})
            quest_name = quest_info.get('name', f"Mission {mission_code}")
            
            # 원본 임베드 가져오기
            original_embed = interaction.message.embeds[0]
            
            # 거부된 임베드 생성
            rejected_embed = discord.Embed(
                title="❌ Submission Rejected",
                color=0xFF0000,  # Red
                timestamp=original_embed.timestamp
            )
            
            # 원본 필드 복사
            for field in original_embed.fields:
                rejected_embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )
            
            # 반려 사유 추가
            rejected_embed.add_field(
                name="❌ Rejection Reason",
                value=reason,
                inline=False
            )
            
            # Footer에 거부자 정보 추가
            rejected_embed.set_footer(text=f"Rejected by {interaction.user.display_name}")
            
            # 버튼 비활성화된 View 생성
            disabled_view = discord.ui.View()
            disabled_view.add_item(
                discord.ui.Button(
                    label="✅ Approve",
                    style=discord.ButtonStyle.green,
                    disabled=True
                )
            )
            disabled_view.add_item(
                discord.ui.Button(
                    label="❌ Rejected",
                    style=discord.ButtonStyle.red,
                    disabled=True
                )
            )
            
            # 메시지 수정
            await interaction.message.edit(embed=rejected_embed, view=disabled_view)
            
            # 사용자에게 DM 전송
            try:
                user = await self.bot.fetch_user(user_id)
                dm_embed = discord.Embed(
                    title="⚠️ Submission Rejected",
                    description=f"Your submission for **{quest_name}** was rejected.",
                    color=discord.Color.red()
                )
                dm_embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
                dm_embed.add_field(
                    name="Next Steps",
                    value="Please check the guidelines and try again using `/sz` command.",
                    inline=False
                )
                await user.send(embed=dm_embed)
            except Exception as e:
                logger.error(
                    "반려 알림 DM 전송 실패 user_id=%s submission_id=%s error=%s",
                    user_id,
                    self.submission_id,
                    e,
                    exc_info=True,
                )
            
            # 성공 메시지
            await interaction.followup.send(
                "✅ Submission rejected. User has been notified.",
                ephemeral=True
            )
            
        except Exception as e:
            logger.exception(
                "거부 처리 중 오류 submission_id=%s admin_id=%s error=%s",
                self.submission_id,
                interaction.user.id,
                e,
            )
            await interaction.followup.send(
                f"❌ 거부 처리 중 오류가 발생했습니다: {str(e)}",
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

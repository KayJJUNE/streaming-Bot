import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from database import Database

# 환경 변수 로드
load_dotenv()

# 로깅 설정 (유저 사용 중 문제 발생 시 로그 출력)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bot")

# 봇 설정
intents = discord.Intents.default()
intents.members = True  # Privileged Intent - Discord Developer Portal에서 활성화 필요
# intents.message_content = True  # 메시지 내용을 읽지 않으므로 불필요

bot = commands.Bot(command_prefix='!', intents=intents)

# 데이터베이스 초기화
db = Database()

@bot.event
async def on_ready():
    print(f'{bot.user}가 로그인했습니다!')
    print(f'봇 ID: {bot.user.id}')
    print(f'서버 수: {len(bot.guilds)}')
    
    # 슬래시 명령어 동기화
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 슬래시 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'명령어 동기화 중 오류 발생: {e}')
    
    # 서버 시작 시 모든 사용자 역할 업데이트 (백그라운드 실행해 슬래시 커맨드 3초 타임아웃 방지)
    asyncio.create_task(update_all_user_roles())

async def update_all_user_roles():
    """서버의 모든 사용자 역할 업데이트. DB 호출은 to_thread로 해서 이벤트 루프(하트비트) 블로킹 방지."""
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                try:
                    user = await asyncio.to_thread(db.get_user, member.id)
                except Exception as e:
                    logger.warning("역할 업데이트용 유저 조회 실패 user_id=%s error=%s", member.id, e)
                    continue
                if user:
                    await update_user_roles(member.id, guild, user=user)

async def update_user_roles(user_id: int, guild: discord.Guild, *, user=None):
    """사용자 역할 업데이트. user가 없으면 to_thread로 조회."""
    from database import TIER_SYSTEM

    if user is None:
        try:
            user = await asyncio.to_thread(db.get_user, user_id)
        except Exception as e:
            logger.warning("역할 업데이트용 유저 조회 실패 user_id=%s error=%s", user_id, e)
            return
    if not user:
        return
    
    member = guild.get_member(user_id)
    if not member:
        return
    
    total_xp = user['total_xp']
    current_tier = db.get_user_tier(total_xp)
    
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
            except discord.Forbidden:
                logger.warning("역할 추가 권한 없음 (서버 역할 순서 확인) user_id=%s role=%s", user_id, role.name)
            except Exception as e:
                logger.warning("역할 추가 실패 user_id=%s role=%s error=%s", user_id, role.name, e)
    
    # 현재 티어보다 높은 역할 제거
    for tier_level in range(current_tier + 1, 6):
        if tier_level in tier_roles:
            role = tier_roles[tier_level]
            if role in member.roles:
                try:
                    await member.remove_roles(role, reason=f"티어 다운그레이드")
                except discord.Forbidden:
                    logger.warning("역할 제거 권한 없음 (서버 역할 순서 확인) user_id=%s role=%s", user_id, role.name)
                except Exception as e:
                    logger.warning("역할 제거 실패 user_id=%s role=%s error=%s", user_id, role.name, e)

@bot.event
async def on_member_join(member: discord.Member):
    """새 멤버가 서버에 참가할 때"""
    if member.bot:
        return
    
    # 사용자 등록
    db.register_user(member.id)
    
    # 기본 역할 부여 (Lv2: SZ Streamer)
    from database import TIER_SYSTEM
    streamer_role = discord.utils.get(member.guild.roles, name=TIER_SYSTEM[2]['role_name'])
    if streamer_role:
        try:
            await member.add_roles(streamer_role, reason="신규 멤버 기본 역할")
        except:
            pass

# Cog 로드
async def load_cogs():
    """모든 Cog 로드"""
    cogs = [
        'cogs.quests',
        'cogs.profile',
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f'✅ {cog} 로드 완료')
        except Exception as e:
            print(f'❌ {cog} 로드 실패: {e}')

@bot.event
async def on_command_error(ctx, error):
    """명령어 오류 처리"""
    if isinstance(error, commands.CommandNotFound):
        return
    user_id = getattr(ctx.author, "id", None)
    logger.error("명령어 오류 user_id=%s command=%s error=%s", user_id, getattr(ctx.command, "name", None), error)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """슬래시 커맨드 실행 중 미처리 예외 발생 시 로그 출력 및 유저에게 안내"""
    user_id = getattr(interaction.user, "id", None)
    user_name = getattr(interaction.user, "display_name", str(user_id))
    command_name = interaction.command.name if interaction.command else "unknown"
    original = getattr(error, "original", error)
    # Unknown interaction (10062): 인터랙션이 이미 만료됨(3초 초과 또는 이벤트 루프 지연). 응답 불가.
    if getattr(original, "code", None) == 10062 or isinstance(original, discord.NotFound):
        logger.warning(
            "인터랙션 만료(봇 응답 지연) user_id=%s user=%s command=%s - 유저에게 커맨드 재실행 안내",
            user_id,
            user_name,
            command_name,
        )
        return
    logger.exception(
        "유저 커맨드 오류 user_id=%s user=%s command=%s error=%s",
        user_id,
        user_name,
        command_name,
        error,
    )
    if not interaction.response.is_done():
        try:
            await interaction.response.send_message(
                "❌ 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                ephemeral=True,
            )
        except Exception:
            try:
                await interaction.followup.send(
                    "❌ 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    ephemeral=True,
                )
            except Exception:
                pass

# 봇 실행
async def main():
    async with bot:
        await load_cogs()
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("❌ 오류: DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
            print("Railway Variables에서 DISCORD_BOT_TOKEN을 설정해주세요.")
            raise ValueError("DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
        
        admin_channel = os.getenv('ADMIN_CHANNEL_ID')
        if not admin_channel or admin_channel == 'your_channel_id_here':
            print("⚠️  경고: ADMIN_CHANNEL_ID가 설정되지 않았습니다.")
            print("관리자 승인 기능이 작동하지 않을 수 있습니다.")
        
        print(f"🔑 토큰 확인: {'✅' if token else '❌'}")
        print(f" channel ID: {'✅' if admin_channel and admin_channel != 'your_channel_id_here' else '❌'}")
        
        await bot.start(token)

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('봇이 종료되었습니다.')
    except Exception as e:
        print(f'오류 발생: {e}')


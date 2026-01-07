import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from database import Database

# 환경 변수 로드
load_dotenv()

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

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
    
    # 서버 시작 시 모든 사용자 역할 업데이트
    await update_all_user_roles()

async def update_all_user_roles():
    """서버의 모든 사용자 역할 업데이트"""
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                user = db.get_user(member.id)
                if user:
                    await update_user_roles(member.id, guild)

async def update_user_roles(user_id: int, guild: discord.Guild):
    """사용자 역할 업데이트"""
    from database import TIER_SYSTEM
    
    user = db.get_user(user_id)
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
            except Exception as e:
                print(f"역할 추가 실패 (User: {user_id}, Role: {role.name}): {e}")
    
    # 현재 티어보다 높은 역할 제거
    for tier_level in range(current_tier + 1, 6):
        if tier_level in tier_roles:
            role = tier_roles[tier_level]
            if role in member.roles:
                try:
                    await member.remove_roles(role, reason=f"티어 다운그레이드")
                except Exception as e:
                    print(f"역할 제거 실패 (User: {user_id}, Role: {role.name}): {e}")

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
    print(f'명령어 오류: {error}')

# 봇 실행
async def main():
    async with bot:
        await load_cogs()
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
        await bot.start(token)

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('봇이 종료되었습니다.')
    except Exception as e:
        print(f'오류 발생: {e}')


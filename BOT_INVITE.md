# Discord 봇 초대 가이드

## "Integration requires code grant" 오류 해결

봇을 서버에 초대할 때 이 오류가 발생하는 이유는 Discord Developer Portal에서 **"Requires OAuth2 Code Grant"** 옵션이 활성화되어 있기 때문입니다.

### 해결 방법

1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. 봇 애플리케이션 선택
3. **"Bot"** 메뉴 클릭
4. **"Authorization Flow"** 섹션에서:
   - **"Requires OAuth2 Code Grant"** 옵션을 **비활성화** (토글 OFF)
5. **"Save Changes"** 클릭

### 봇 초대 링크 생성

1. Discord Developer Portal에서 **"OAuth2"** → **"URL Generator"** 클릭
2. **Scopes**에서 선택:
   - ✅ `bot`
   - ✅ `applications.commands` (슬래시 명령어용)
3. **Bot Permissions**에서 선택:
   - ✅ `Manage Roles` (역할 관리)
   - ✅ `Send Messages` (메시지 전송)
   - ✅ `Embed Links` (임베드 링크)
   - ✅ `Read Message History` (메시지 기록 읽기)
   - ✅ `Use Slash Commands` (슬래시 명령어 사용)
4. 하단에 생성된 **"Generated URL"** 복사
5. 브라우저에서 해당 URL 열기
6. 서버 선택 후 승인

### 참고

- **"Requires OAuth2 Code Grant"**는 특별한 OAuth2 플로우가 필요한 복잡한 애플리케이션에서만 사용합니다
- 일반 Discord 봇은 이 옵션을 비활성화해도 정상 작동합니다
- 이 옵션을 비활성화하면 일반 초대 링크로 바로 봇을 초대할 수 있습니다


# Railway 배포 가이드

## 1. Discord Developer Portal 설정

### 봇 초대 설정

1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. 봇 애플리케이션 선택
3. 왼쪽 메뉴에서 **"Bot"** 클릭
4. **"Authorization Flow"** 섹션에서:
   - ✅ **Public Bot**: 활성화 (누구나 봇을 추가할 수 있음)
   - ❌ **Requires OAuth2 Code Grant**: **비활성화** (일반 초대 링크 사용)
     - 이 옵션이 활성화되어 있으면 "Integration requires code grant" 오류가 발생합니다
     - 대부분의 봇은 이 옵션을 비활성화해도 정상 작동합니다

### Privileged Intents 활성화

5. **"Privileged Gateway Intents"** 섹션에서 다음을 활성화:
   - ✅ **SERVER MEMBERS INTENT** (필수) - 멤버 목록 접근용
   - ❌ **MESSAGE CONTENT INTENT** (불필요) - 메시지 내용 읽기용 (현재 봇에서는 사용 안 함)
   - ❌ **PRESENCE INTENT** (불필요) - 사용자 상태 확인용

6. **"Save Changes"** 클릭

## 2. Railway 환경 변수 설정

Railway 대시보드에서 다음 환경 변수를 설정하세요:

## 2.1 Python 버전 고정 (중요)

Railway 빌드 과정에서 `mise`가 Python을 자동 설치할 때, **지원되지 않는 버전(예: 3.13.x)** 을 잡으면 설치가 실패할 수 있습니다.

이 레포는 `.tool-versions` / `.python-version` 으로 **Python 3.12.9** 를 고정했습니다.

만약 빌드 로그에서 Python 설치 오류가 계속 나오면:
- Railway에서 캐시 삭제 후 재배포하거나
- `.tool-versions`의 버전을 3.12.x 다른 버전으로 바꿔 재시도하세요.

### 필수 환경 변수

1. **DISCORD_BOT_TOKEN**
   - 값: Discord Developer Portal에서 발급받은 봇 토큰을 입력하세요

2. **ADMIN_CHANNEL_ID**
   - 값: `1417465862910246922` (관리자 승인 채널 ID)
   - 채널 링크: https://discord.com/channels/1371432049621078046/1417465862910246922

3. **DATABASE_URL** (PostgreSQL)
   - Railway에서 PostgreSQL 서비스를 추가하면 자동으로 설정됩니다
   - 또는 수동으로 설정:
     - `postgresql://postgres:FpTkzkYnfRCwbbxGlkriLBEUkCDAFAsd@switchyard.proxy.rlwy.net:11525/railway`
   - **참고:** Railway에서 PostgreSQL 서비스를 추가하면 `DATABASE_URL` 환경 변수가 자동으로 생성됩니다

### Railway에서 환경 변수 설정 방법

1. Railway 프로젝트 대시보드 접속
2. 서비스 선택
3. **"Variables"** 탭 클릭
4. **"New Variable"** 클릭
5. 변수 이름과 값 입력:
   - Name: `DISCORD_BOT_TOKEN`
   - Value: Discord Developer Portal에서 발급받은 봇 토큰
6. **"Add"** 클릭
7. `ADMIN_CHANNEL_ID`도 동일하게 추가

### Discord 채널 ID 확인 방법

1. Discord에서 개발자 모드 활성화:
   - 사용자 설정 → 고급 → 개발자 모드 활성화
2. 관리자 승인 채널에서 우클릭
3. **"ID 복사"** 선택
4. 복사한 ID를 `ADMIN_CHANNEL_ID`에 입력

## 3. Railway 배포 확인

### 배포 후 확인사항

1. Railway 로그에서 다음 메시지 확인:
   ```
   ✅ cogs.quests 로드 완료
   ✅ cogs.profile 로드 완료
   [봇 이름]가 로그인했습니다!
   ```

2. Discord에서 봇 상태 확인:
   - 봇이 온라인 상태여야 합니다
   - `/sz` 명령어가 작동해야 합니다

### 문제 해결

#### 봇이 오프라인인 경우

1. **Privileged Intents 확인**
   - Discord Developer Portal에서 SERVER MEMBERS INTENT가 활성화되어 있는지 확인

2. **환경 변수 확인**
   - Railway Variables 탭에서 `DISCORD_BOT_TOKEN`이 올바르게 설정되었는지 확인
   - 토큰에 공백이나 따옴표가 없는지 확인

3. **로그 확인**
   - Railway 로그에서 오류 메시지 확인
   - "privileged intents" 오류가 있으면 위의 1번 단계 확인

#### 명령어가 보이지 않는 경우

1. 봇이 온라인 상태인지 확인
2. 몇 분 기다린 후 다시 시도 (슬래시 명령어 동기화에 시간이 걸릴 수 있음)
3. Discord 서버에서 봇을 다시 초대 (필요한 경우)

## 4. 봇 재시작

환경 변수를 변경한 경우:

1. Railway 대시보드에서 서비스 선택
2. **"Deployments"** 탭 클릭
3. 최신 배포 옆의 **"..."** 메뉴 클릭
4. **"Redeploy"** 선택

또는

1. **"Settings"** 탭 클릭
2. **"Restart"** 버튼 클릭


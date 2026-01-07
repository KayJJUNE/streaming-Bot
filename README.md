# Spot Zero Ambassador Program Discord Bot

Discord 봇으로 Spot Zero Ambassador Program의 퀘스트 시스템을 관리합니다.

## 기능

- ✅ 퀘스트 제출 및 관리자 승인 시스템
- ✅ 자동 XP 및 티어 시스템
- ✅ 누적 마일스톤 퀘스트 자동 완료
- ✅ Discord 역할 자동 부여
- ✅ 프로필 및 리더보드 시스템

## 설치 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 입력하세요:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
ADMIN_CHANNEL_ID=your_channel_id_here
```

**중요:** `env.example` 파일을 참고하여 `.env` 파일을 생성하세요. `.env` 파일은 Git에 커밋되지 않습니다 (보안상의 이유).

### 3. Discord 봇 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성
2. 봇 토큰을 `.env` 파일에 입력
3. 봇에 다음 권한 부여:
   - Manage Roles
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands

### 4. 서버 역할 생성

다음 역할들을 서버에 생성하세요 (정확한 이름으로):

- `Code SZ` (Lv1)
- `SZ Streamer` (Lv2)
- `SZ Elite` (Lv3)
- `SZ Ambassador` (Lv4)
- `SZ Partner` (Lv5)

**중요:** 역할의 순서가 중요합니다. 봇이 역할을 부여할 때 서버 역할 목록의 순서를 따릅니다.

### 5. 봇 실행

```bash
python main.py
```

또는

```bash
python3 main.py
```

## 명령어

### 사용자 명령어

- `/sz` - 퀘스트 보드 확인 및 제출
  - 퀘스트 보드를 확인하고 "퀘스트 제출" 버튼을 클릭하여 제출
  - 멀티 모달 형식으로 퀘스트 선택 및 링크 입력
  - 반려된 제출 내용도 확인 가능
  - 제출 완료 시 "24시간 내 확인할 수 있습니다" 안내

- `/ranking` - 랭킹 보드 확인
  - 상위 20명의 사용자 표시
  - 자신이 20위 밖에 있으면 하단에 자신의 순위와 점수 표시

### 관리자 기능

- 제출된 퀘스트는 `ADMIN_CHANNEL_ID`로 지정된 채널에 자동으로 전송됩니다.
- 관리자는 "승인" 또는 "거부" 버튼을 클릭하여 제출을 처리할 수 있습니다.
- 반려 시 반려 사유를 입력해야 하며, 사용자는 `/sz` 명령어로 반려 내용을 확인할 수 있습니다.
- 반려된 제출은 재제출 가능합니다.

## 퀘스트 시스템

### 직접 제출 퀘스트

- **Mission A:** SNF Promo Video (150 XP, 원타임)
- **Mission B:** Upload 1 Video (80 XP, 반복 가능)
- **Mission C:** Live Stream 1 Time (100 XP, 반복 가능)
- **Mission H:** High Engagement (1,500 XP, 원타임, 스냅샷 필요)

### 마일스톤 퀘스트 (자동 완료)

- **Mission D:** 5개 비디오 승인 시 (200 XP)
- **Mission E:** 10개 비디오 승인 시 (500 XP)
- **Mission F:** 3개 스트림 승인 시 (150 XP)
- **Mission G:** 6개 스트림 승인 시 (300 XP)

## 티어 시스템

- **Lv1: Code SZ** (0 XP) - 기본 역할
- **Lv2: SZ Streamer** (0 XP) - 등록 시 자동 부여
- **Lv3: SZ Elite** (500 XP)
- **Lv4: SZ Ambassador** (1,000 XP)
- **Lv5: SZ Partner** (2,500 XP)

## 데이터베이스

SQLite 데이터베이스 (`database.db`)에 다음 정보가 저장됩니다:

- 사용자 정보 (XP, 레벨)
- 제출 기록
- 완료된 퀘스트 기록

## 문제 해결

### 역할이 부여되지 않는 경우

1. 봇의 역할이 부여하려는 역할보다 위에 있는지 확인
2. 역할 이름이 정확한지 확인
3. 봇에 "Manage Roles" 권한이 있는지 확인

### 명령어가 보이지 않는 경우

1. 봇을 재시작하세요
2. `/`를 입력했을 때 명령어가 나타나는지 확인
3. 봇이 서버에 있는지 확인

## 라이선스

이 프로젝트는 Spot Zero Ambassador Program을 위해 제작되었습니다.

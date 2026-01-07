import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import json

# 퀘스트 정보 정의
QUEST_INFO = {
    'A': {'name': 'SNF Promo Video', 'xp': 150, 'type': 'one-time', 'requires_snapshot': False},
    'B': {'name': 'Upload 1 Video', 'xp': 80, 'type': 'repeatable', 'requires_snapshot': False},
    'C': {'name': 'Live Stream 1 Time', 'xp': 100, 'type': 'repeatable', 'requires_snapshot': False},
    'D': {'name': 'Accumulate 5 approved Videos', 'xp': 200, 'type': 'milestone', 'requires_snapshot': False},
    'E': {'name': 'Accumulate 10 approved Videos', 'xp': 500, 'type': 'milestone', 'requires_snapshot': False},
    'F': {'name': 'Accumulate 3 approved Live Streams', 'xp': 150, 'type': 'milestone', 'requires_snapshot': False},
    'G': {'name': 'Accumulate 6 approved Live Streams', 'xp': 300, 'type': 'milestone', 'requires_snapshot': False},
    'H': {'name': 'High Engagement', 'xp': 1500, 'type': 'one-time', 'requires_snapshot': True},
}

# 티어 시스템 정의
TIER_SYSTEM = {
    1: {'name': 'Code SZ', 'xp_required': 0, 'role_name': 'Code SZ'},
    2: {'name': 'SZ Streamer', 'xp_required': 0, 'role_name': 'SZ Streamer'},
    3: {'name': 'SZ Elite', 'xp_required': 500, 'role_name': 'SZ Elite'},
    4: {'name': 'SZ Ambassador', 'xp_required': 1000, 'role_name': 'SZ Ambassador'},
    5: {'name': 'SZ Partner', 'xp_required': 2500, 'role_name': 'SZ Partner'},
}

class Database:
    def __init__(self):
        """PostgreSQL 데이터베이스 초기화"""
        self.connection_string = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL 또는 DATABASE_PUBLIC_URL 환경 변수가 설정되지 않았습니다.")
        self.init_database()
    
    def get_connection(self):
        """데이터베이스 연결 반환"""
        conn = psycopg2.connect(self.connection_string)
        return conn
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 사용자 테이블 (새로운 구조)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    total_submissions INTEGER DEFAULT 0,
                    approved_count INTEGER DEFAULT 0,
                    total_xp INTEGER DEFAULT 0,
                    link_list TEXT[] DEFAULT '{}',
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 제출 기록 테이블 (상세 기록용)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    submission_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    mission_code VARCHAR(10) NOT NULL,
                    link TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    rejection_reason TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # 완료된 퀘스트 기록 테이블 (마일스톤 포함)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS completed_quests (
                    completion_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    mission_code VARCHAR(10) NOT NULL,
                    xp_earned INTEGER NOT NULL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, mission_code)
                )
            ''')
            
            # XP 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS xp_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    mission_name VARCHAR(255) NOT NULL,
                    xp_amount INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_submissions_user 
                ON submissions(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_submissions_status 
                ON submissions(status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_completed_quests_user 
                ON completed_quests(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_xp_logs_user 
                ON xp_logs(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_xp_logs_created_at 
                ON xp_logs(created_at DESC)
            ''')
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ 데이터베이스 초기화 오류: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def register_user(self, user_id: int) -> bool:
        """사용자 등록 (처음 사용 시)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (user_id) 
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"❌ 사용자 등록 오류: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """사용자 정보 조회"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_or_create_user(self, user_id: int) -> Dict:
        """사용자 정보 조회 또는 생성"""
        user = self.get_user(user_id)
        if not user:
            self.register_user(user_id)
            user = self.get_user(user_id)
        return user
    
    def create_submission(self, user_id: int, mission_code: str, link: str) -> int:
        """제출 생성"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 제출 기록 추가
            cursor.execute('''
                INSERT INTO submissions (user_id, mission_code, link, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING submission_id
            ''', (user_id, mission_code, link))
            
            submission_id = cursor.fetchone()[0]
            
            # 사용자 테이블 업데이트 (total_submissions, link_list)
            cursor.execute('''
                UPDATE users
                SET total_submissions = total_submissions + 1,
                    link_list = array_append(link_list, %s)
                WHERE user_id = %s
            ''', (link, user_id))
            
            conn.commit()
            return submission_id
        except Exception as e:
            conn.rollback()
            print(f"❌ 제출 생성 오류: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_submission(self, submission_id: int) -> Optional[Dict]:
        """제출 정보 조회"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('SELECT * FROM submissions WHERE submission_id = %s', (submission_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            cursor.close()
            conn.close()
    
    def approve_submission(self, submission_id: int) -> Tuple[bool, Optional[str], List[Dict]]:
        """제출 승인 및 XP 추가"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 제출 정보 조회
            submission = self.get_submission(submission_id)
            if not submission:
                return False, "제출을 찾을 수 없습니다.", []
            
            if submission['status'] != 'pending':
                return False, "이미 처리된 제출입니다.", []
            
            user_id = submission['user_id']
            mission_code = submission['mission_code']
            
            # 원타임 퀘스트 중복 체크
            quest_info = QUEST_INFO.get(mission_code)
            if not quest_info:
                return False, "유효하지 않은 미션 코드입니다.", []
            
            if quest_info['type'] == 'one-time':
                cursor.execute('''
                    SELECT COUNT(*) FROM completed_quests
                    WHERE user_id = %s AND mission_code = %s
                ''', (user_id, mission_code))
                if cursor.fetchone()[0] > 0:
                    return False, "이미 완료한 원타임 퀘스트입니다.", []
            
            # 제출 상태 업데이트
            cursor.execute('''
                UPDATE submissions
                SET status = 'approved', approved_at = CURRENT_TIMESTAMP
                WHERE submission_id = %s
            ''', (submission_id,))
            
            # XP 추가 및 사용자 테이블 업데이트
            xp_earned = quest_info['xp']
            mission_name = f"Mission {mission_code}: {quest_info['name']}"
            
            cursor.execute('''
                UPDATE users
                SET total_xp = total_xp + %s,
                    approved_count = approved_count + 1
                WHERE user_id = %s
            ''', (xp_earned, user_id))
            
            # XP 로그 기록
            cursor.execute('''
                INSERT INTO xp_logs (user_id, mission_name, xp_amount)
                VALUES (%s, %s, %s)
            ''', (user_id, mission_name, xp_earned))
            
            # 완료된 퀘스트 기록 (원타임만 기록)
            if quest_info['type'] == 'one-time':
                cursor.execute('''
                    INSERT INTO completed_quests (user_id, mission_code, xp_earned)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, mission_code) DO NOTHING
                ''', (user_id, mission_code, xp_earned))
            
            conn.commit()
            
            # 누적 마일스톤 체크
            milestone_rewards = self._check_milestones(user_id, mission_code, cursor)
            
            conn.commit()
            return True, f"{xp_earned} XP를 획득했습니다.", milestone_rewards
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 승인 처리 오류: {e}")
            return False, f"오류 발생: {str(e)}", []
        finally:
            cursor.close()
            conn.close()
    
    def _check_milestones(self, user_id: int, approved_mission: str, cursor) -> List[Dict]:
        """누적 마일스톤 체크 및 보상 지급"""
        rewards = []
        
        # Mission B (비디오) 승인 시 D, E 체크
        if approved_mission == 'B':
            cursor.execute('''
                SELECT COUNT(*) FROM submissions
                WHERE user_id = %s AND mission_code = 'B' AND status = 'approved'
            ''', (user_id,))
            video_count = cursor.fetchone()[0]
            
            # Mission D: 5개 비디오
            if video_count == 5:
                if self._grant_milestone(user_id, 'D', cursor):
                    rewards.append({'mission': 'D', 'xp': 200})
            
            # Mission E: 10개 비디오
            if video_count == 10:
                if self._grant_milestone(user_id, 'E', cursor):
                    rewards.append({'mission': 'E', 'xp': 500})
        
        # Mission C (스트리밍) 승인 시 F, G 체크
        elif approved_mission == 'C':
            cursor.execute('''
                SELECT COUNT(*) FROM submissions
                WHERE user_id = %s AND mission_code = 'C' AND status = 'approved'
            ''', (user_id,))
            stream_count = cursor.fetchone()[0]
            
            # Mission F: 3개 스트림
            if stream_count == 3:
                if self._grant_milestone(user_id, 'F', cursor):
                    rewards.append({'mission': 'F', 'xp': 150})
            
            # Mission G: 6개 스트림
            if stream_count == 6:
                if self._grant_milestone(user_id, 'G', cursor):
                    rewards.append({'mission': 'G', 'xp': 300})
        
        return rewards
    
    def _grant_milestone(self, user_id: int, mission_code: str, cursor) -> bool:
        """마일스톤 보상 지급"""
        quest_info = QUEST_INFO.get(mission_code)
        if not quest_info:
            return False
        
        # 이미 완료했는지 체크
        cursor.execute('''
            SELECT COUNT(*) FROM completed_quests
            WHERE user_id = %s AND mission_code = %s
        ''', (user_id, mission_code))
        if cursor.fetchone()[0] > 0:
            return False
        
        # XP 추가
        xp_earned = quest_info['xp']
        mission_name = f"Mission {mission_code}: {quest_info['name']} (Milestone)"
        
        cursor.execute('''
            UPDATE users
            SET total_xp = total_xp + %s
            WHERE user_id = %s
        ''', (xp_earned, user_id))
        
        # XP 로그 기록
        cursor.execute('''
            INSERT INTO xp_logs (user_id, mission_name, xp_amount)
            VALUES (%s, %s, %s)
        ''', (user_id, mission_name, xp_earned))
        
        # 완료 기록
        cursor.execute('''
            INSERT INTO completed_quests (user_id, mission_code, xp_earned)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, mission_code) DO NOTHING
        ''', (user_id, mission_code, xp_earned))
        
        return True
    
    def reject_submission(self, submission_id: int, reason: str = None) -> bool:
        """제출 거부"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE submissions
                SET status = 'rejected', rejection_reason = %s
                WHERE submission_id = %s
            ''', (reason, submission_id))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ 거부 처리 오류: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_rejected_submissions(self, user_id: int) -> List[Dict]:
        """사용자의 반려된 제출 목록 조회"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT * FROM submissions
                WHERE user_id = %s AND status = 'rejected'
                ORDER BY submitted_at DESC
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    
    def get_user_submissions(self, user_id: int, status: Optional[str] = None) -> List[Dict]:
        """사용자의 제출 목록 조회"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            if status:
                cursor.execute('''
                    SELECT * FROM submissions
                    WHERE user_id = %s AND status = %s
                    ORDER BY submitted_at DESC
                ''', (user_id, status))
            else:
                cursor.execute('''
                    SELECT * FROM submissions
                    WHERE user_id = %s
                    ORDER BY submitted_at DESC
                ''', (user_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    
    def get_approved_count(self, user_id: int, mission_code: str) -> int:
        """승인된 특정 미션 개수"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM submissions
                WHERE user_id = %s AND mission_code = %s AND status = 'approved'
            ''', (user_id, mission_code))
            
            count = cursor.fetchone()[0]
            return count
        finally:
            cursor.close()
            conn.close()
    
    def is_quest_completed(self, user_id: int, mission_code: str) -> bool:
        """원타임 퀘스트 완료 여부"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM completed_quests
                WHERE user_id = %s AND mission_code = %s
            ''', (user_id, mission_code))
            
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            cursor.close()
            conn.close()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """리더보드 조회"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT user_id, total_xp, approved_count, total_submissions
                FROM users
                ORDER BY total_xp DESC
                LIMIT %s
            ''', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
    
    def get_user_tier(self, total_xp: int) -> int:
        """XP에 따른 티어 계산"""
        tier = 1
        for tier_level, tier_info in sorted(TIER_SYSTEM.items(), reverse=True):
            if total_xp >= tier_info['xp_required']:
                tier = tier_level
                break
        return tier
    
    def get_pending_submissions(self) -> List[Dict]:
        """대기 중인 제출 목록"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT * FROM submissions
                WHERE status = 'pending'
                ORDER BY submitted_at ASC
            ''')
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()

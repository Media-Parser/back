# service/node/03_context/detect_chage.py

import hashlib
from typing import List, Dict, Any
from textwrap import dedent
import difflib

class DocumentManager:
    """
    복합 청킹 전략을 사용하고, 청크 단위의 추가/삭제/변경을 감지하는 클래스.
    """
    def __init__(self):
        self.chunks: List[str] = []
        self.hashes: List[str] = []
        print("✅ DocumentManager가 초기화되었습니다.")

    def _get_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _chunk_text(self, text: str, max_chunk_size: int) -> List[str]:
        """줄 단위로 나누고, 긴 줄은 글자 수에 맞춰 다시 나누는 메서드."""
        final_chunks = []
        lines = text.strip().splitlines()
        for line in lines:
            if len(line) <= max_chunk_size:
                final_chunks.append(line)
            else:
                for i in range(0, len(line), max_chunk_size):
                    final_chunks.append(line[i:i + max_chunk_size])
        return final_chunks

    def load_document(self, full_document: str, max_chunk_size: int = 80):
        clean_document = dedent(full_document)
        self.chunks = self._chunk_text(clean_document, max_chunk_size)
        self.hashes = [self._get_hash(chunk) for chunk in self.chunks]
        print(f"📄 문서 로드 완료. 총 {len(self.chunks)}개의 청크가 생성되었습니다.")

    # 🎯 깃허브 스타일 diff 생성 로직 제거하고 단순화
    def find_and_update_changes(self, new_full_document: str, max_chunk_size: int = 80) -> Dict[str, List[int]]:
        """
        청크 단위로 추가, 삭제, 변경을 감지하고 해당 인덱스 목록을 반환합니다.
        """
        print("\n--- [단순 청크 단위] 변경사항 감지 시작 ---")
        clean_document = dedent(new_full_document)
        new_chunks = self._chunk_text(clean_document, max_chunk_size)
        new_hashes = [self._get_hash(chunk) for chunk in new_chunks]

        matcher = difflib.SequenceMatcher(None, self.hashes, new_hashes)
        changes: Dict[str, List[int]] = {"modified": [], "deleted": [], "inserted": []}
        has_changes = False

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                # 변경된 청크의 인덱스만 기록
                changes["modified"].extend(range(j1, j2))
                has_changes = True
            elif tag == 'delete':
                changes["deleted"].extend(range(i1, i2))
                has_changes = True
            elif tag == 'insert':
                changes["inserted"].extend(range(j1, j2))
                has_changes = True
        
        if not has_changes:
            print("ℹ️ 문서에 변경사항이 없습니다.")
            return {}

        self.chunks = new_chunks
        self.hashes = new_hashes
        print("🔄 문서 상태가 최신으로 동기화되었습니다.")
        return changes

    # get_context 메서드는 변경 없음
    def get_context(self, focus_index: int, max_tokens: int) -> str:
        if not (0 <= focus_index < len(self.chunks)): return "에러"
        def _estimate_tokens(text: str) -> int: return len(text.split())
        context_chunks = [self.chunks[focus_index]]
        current_tokens = _estimate_tokens(self.chunks[focus_index])
        left, right = focus_index - 1, focus_index + 1
        while current_tokens < max_tokens:
            added_something = False
            if right < len(self.chunks):
                chunk_to_add = self.chunks[right]
                chunk_tokens = _estimate_tokens(chunk_to_add)
                if current_tokens + chunk_tokens <= max_tokens:
                    context_chunks.append(chunk_to_add); current_tokens += chunk_tokens; added_something = True
                right += 1
            if left >= 0:
                chunk_to_add = self.chunks[left]
                chunk_tokens = _estimate_tokens(chunk_to_add)
                if current_tokens + chunk_tokens <= max_tokens:
                    context_chunks.insert(0, chunk_to_add); current_tokens += chunk_tokens; added_something = True
                left -= 1
            if not added_something: break
        print(f"📦 컨텍스트 구성 완료 (포커스: {focus_index}번 청크)")
        return "\n".join(context_chunks)

# --- 사용 예시 ---
if __name__ == "__main__":
    manager = DocumentManager()

    # 1. 초기 문서 로드
    initial_document = """
        첫 번째 줄은 짧습니다.
        두 번째 줄은 아주 깁니다. 이 줄은 설정된 최대 청크 크기인 80자를 초과하므로, 로드될 때 여러 개의 작은 청크로 자동으로 나뉘어야 합니다. 이 부분이 핵심 테스트 포인트입니다.
        세 번째 줄도 짧습니다."""
    
    print("\n--- 1. 초기 문서 로드 ---")
    manager.load_document(initial_document, max_chunk_size=80)

    # 2. 긴 줄의 중간 부분만 수정한 문서를 준비
    modified_document = """첫 번째 줄은 짧습니다.
        두 번째 줄은 아주 깁니다. 이 줄은 설정된 최대 청크 크기인 80자를 초과하므로, 로드될 때 여러 개의 작은 청크로 바뀌어서 테스트되어야 합니다. 이 부분이 핵심 테스트 포인트입니다.
        세"""

    # 3. 변경사항을 찾고 인덱스 목록을 확인
    changes_dict = manager.find_and_update_changes(modified_document, max_chunk_size=80)

    if changes_dict:
        print(f"\n--- 감지된 변경 내역 (인덱스) ---")
        print(changes_dict)
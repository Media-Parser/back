# app/utils/parse.py
import re
from typing import List, Dict

def parse_generated_output(output: str) -> List[Dict[str, str]]:
    """
    생성 모델 출력에서 라벨과 하이라이트된 텍스트를 추출합니다.
    예시:
    감정적 비난: [START]정신 나간[END]
    → [{"label": "감정적 비난", "highlight": "정신 나간"}]
    """
    pattern = re.compile(r"(.+?):\s*\[START\](.+?)\[END\]")
    results = []
    for match in pattern.finditer(output):
        label, span = match.group(1).strip(), match.group(2).strip()
        results.append({"label": label, "highlight": span})

    if not results and output.strip() == "- 문제 없음":
        results.append({"label": "문제 없음", "highlight": ""})

    return results
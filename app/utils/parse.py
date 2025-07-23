# ✅ app/utils/parse.py
import re

def parse_generated_output(text: str):
    text = text.strip()

    if text == "문제 없음":
        return [{"label": "문제 없음", "highlight": ""}]

    pattern = r"([\w가-힣\s/]+?):\s*\[START\](.+?)\[END\]"
    matches = re.findall(pattern, text)

    if matches:
        return [{"label": label.strip(), "highlight": span.strip()} for label, span in matches]

    # fallback: [START]/[END] 없이 단순 라벨: 스팬 형식 지원
    simple_pattern = r"([\w가-힣\s/]+?):\s*(.+)"
    lines = text.splitlines()
    results = []

    for line in lines:
        try:
            match = re.match(simple_pattern, line.strip())
            if match:
                label = match.group(1).strip()
                span = match.group(2).strip()
                if label:  # 라벨 존재 확인
                    results.append({"label": label, "highlight": span})
        except Exception as e:
            print(f"[❌ 파싱 예외] {line} → {e}")
    return results
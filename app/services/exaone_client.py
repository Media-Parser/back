# app/services/exaone_client.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, "../ai/finetuned_exaone"))

print("MODEL_PATH:", MODEL_PATH)

LABEL_EXPLANATIONS = {
    "프레이밍": "논란이 될만한 워딩, 의도적 프레이밍",
    "단정/확증편향": "도약적 일반화, 성급한 단정 등",
    "감정적 비난": "감정적/과장된 비난, 저주성 발언",
    "부정적 표현": "부정적인 단어 혹은 표현 사용",
    "인신공격": "집단, 개인을 대상으로 하는 공격적/비하적 발언",
    "조롱": "조롱, 비아냥, 풍자성 발언",
    "부정적 비유": "부정적인 사물을 비유로 사용하는 경우",
    "책임 전가": "모든 책임을 상대에게 과도하게 전가",
    "극단적 묘사": "상황, 인물을 극단적으로 묘사",
    "일반화": "개별 사례를 집단 전체로 일반화",
    "사실 여부 불명확": "진위 여부가 불명확하거나 확인이 어려움",
    "욕설": "명백한 욕설/비속어"
}


# 아직 파인튜닝 모델 없음
# tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
# model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, trust_remote_code=True)

# 파인튜닝 train.csv에서 매핑 테이블 생성
CSV_PATH = os.path.abspath(os.path.join(BASE_DIR, "../finetune/train.csv"))
df = pd.read_csv(CSV_PATH)
highlight_map = {}  # (문장, 라벨) -> 문제부분
for _, row in df.iterrows():
    highlight_map[(row["sentence"], row["label"])] = row["problematic"]

# def run_exaone_batch(sentences):
#     results = []
#     for sent in sentences:
#         inputs = tokenizer(sent, return_tensors="pt", truncation=True, padding=True, max_length=128)
#         with torch.no_grad():
#             outputs = model(**inputs)
#             pred = outputs.logits.argmax(dim=-1).item()
#             id2label = model.config.id2label
#             label = id2label[str(pred)] if isinstance(pred, int) else id2label[pred]
#             explanation = LABEL_EXPLANATIONS.get(label, "")
#             problematic = highlight_map.get((sent, label), "")  # (문장, 라벨)에 맞는 하이라이트 반환
#         results.append({
#             "sentence": sent,
#             "label": label,
#             "problematic": problematic,    # 문제 부분(하이라이트)
#             "explanation": explanation     # 라벨 설명
#         })
#     return results

def run_exaone_batch(sentences):
    # 아직 파인튜닝 모델 없음
    return [
        {
            "sentence": sent,
            "label": "미지원",
            "problematic": "",
            "explanation": "파인튜닝된 모델이 아직 준비되지 않았습니다."
        }
        for sent in sentences
    ]
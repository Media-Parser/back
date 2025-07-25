# app/services/test.py

import os
import torch
import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def main():
    """
    학습이 완료된 분류 모델을 로드하여
    새로운 문장에 대한 예측을 수행하는 테스트 스크립트.
    """
    # --- 1. 경로 및 모델 설정 ---
    try:
        MODEL_PATH = "/home/ubuntu/ai/finetuned_exaone" 

        print(f"Loading model from: {MODEL_PATH}")

        # --- 2. 라벨 정보 및 모델 로드 ---
        with open(os.path.join(MODEL_PATH, "id2label.json"), 'r') as f:
            id2label = {int(k): v for k, v in json.load(f).items()}
        with open(os.path.join(MODEL_PATH, "label2id.json"), 'r') as f:
            label2id = json.load(f)

        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_PATH,
            local_files_only=True,
            num_labels=len(id2label),
            id2label=id2label,
            label2id=label2id,
            trust_remote_code=True
        )
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        print("✅ 모델 및 토크나이저 로드 완료!")

    except FileNotFoundError:
        print(f"❌ 에러: '{MODEL_PATH}' 경로에 모델 파일이 없습니다.")
        print("학습이 완료되었는지 확인해주세요.")
        return
    except Exception as e:
        print(f"❌ 모델 로드 중 에러 발생: {e}")
        return

    # --- 3. 테스트할 문장 목록 ---
    sentences_to_test = [
        "민주당의 통제 불능에 가까운 입법 폭주가 현실화하고 있습니다.",
        "거대 야당의 폭주가 22대 국회마저도 집어삼키고 말 것이라는 우려가 현실화하고 있습니다.",
        "아니면 이 정도 망언과 그릇된 성 인식은 자신의 허물에 비해서는 비교도 되지 않을 만큼 가볍다고 생각하십니까?",
        "이재명 대표의 사법 리스크가 현실화하고 있다.",
        "오늘 점심 메뉴는 정말 맛있었다.",
        "이런 미친놈을 봤나" # 욕설 테스트
    ]

    print("\n--- 테스트 시작 ---")
    # --- 4. 예측 수행 ---
    with torch.no_grad():
        for text in sentences_to_test:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            outputs = model(**inputs)
            predicted_id = torch.argmax(outputs.logits, dim=-1).item()
            predicted_label = model.config.id2label[predicted_id]
            
            print(f"문장: '{text}'")
            print(f"  -> 예측 라벨: {predicted_label}\n")

if __name__ == '__main__':
    main()
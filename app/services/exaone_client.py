# app/services/exaone_client.py
import torch
import os
import sys
import json
import re
import chardet
import pandas as pd
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel # [추가] PEFT 모델을 직접 로드하기 위해 임포트

# --- 경로 설정 ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
services_dir = current_file_dir
app_dir = os.path.dirname(services_dir)
ssami_back_dir = os.path.dirname(app_dir)
ssami_dir = os.path.dirname(ssami_back_dir)
HOME_DIR = os.path.dirname(ssami_dir)

if HOME_DIR not in sys.path:
    sys.path.append(HOME_DIR)

from finetune.utils.prompt_parser import parse_labels_from_prompt_file

# --- 모델 및 데이터 경로 설정 ---
FINETUNED_MODEL_PATH = os.path.join(HOME_DIR, "ai", "finetuned_exaone_v3")
PROMPT_TEMPLATE_FILE = os.path.join(HOME_DIR, "finetune", "prompt_definitions", "classification_prompt.txt")
SLANGS_FOLDER_PATH = os.path.join(HOME_DIR, "finetune", "slangs")

# --- 전역 변수 선언 ---
tokenizer = None
model = None
device = None
LABEL_EXPLANATIONS = {}
ALL_BADWORDS = set()
HIGHLIGHT_EXAMPLES = {}

def load_dependencies():
    global tokenizer, model, device, LABEL_EXPLANATIONS, ALL_BADWORDS, HIGHLIGHT_EXAMPLES

    # ... (라벨 설명, 비속어 사전 로드는 기존과 동일) ...
    try:
        LABEL_EXPLANATIONS = parse_labels_from_prompt_file(PROMPT_TEMPLATE_FILE)
        print("[INFO] 라벨 설명 로드 완료.")
    except Exception as e:
        print(f"[ERROR] 라벨 설명 로드 실패: {e}")
    try:
        slang_csv_path = os.path.join(SLANGS_FOLDER_PATH, "slang.csv")
        lol_txt_path = os.path.join(SLANGS_FOLDER_PATH, "리그오브레전드_필터링리스트_2020.txt")
        # ... (파일 읽기 로직 생략) ...
        slang_df = pd.read_csv(slang_csv_path, encoding=chardet.detect(open(slang_csv_path, 'rb').read())['encoding'])
        with open(lol_txt_path, encoding=chardet.detect(open(lol_txt_path, 'rb').read())['encoding']) as f:
            lol_words = set(line.strip() for line in f if line.strip())
        slang_words = set()
        for col in slang_df.columns:
            slang_words.update(slang_df[col].dropna().astype(str).str.strip())
        ALL_BADWORDS = slang_words | lol_words
        print(f"[INFO] 비속어 사전 로드 완료. (총 {len(ALL_BADWORDS)}개)")
    except Exception as e:
        print(f"[ERROR] 비속어 사전 로드 실패: {e}")


    # --- [핵심 수정] 모델 로딩 로직 변경 ---
    try:
        print(f"[INFO] 분류 모델 로드 중: {FINETUNED_MODEL_PATH}...")
        BASE_MODEL_PATH = os.path.join(HOME_DIR, "ai", "exaone_small")

        with open(os.path.join(FINETUNED_MODEL_PATH, "id2label.json"), 'r') as f:
            id2label = {int(k): v for k, v in json.load(f).items()}
        with open(os.path.join(FINETUNED_MODEL_PATH, "label2id.json"), 'r') as f:
            label2id = json.load(f)

        # 1. 파인튜닝된 토크나이저를 먼저 로드합니다 (정확한 단어 사전 크기 확보).
        tokenizer = AutoTokenizer.from_pretrained(FINETUNED_MODEL_PATH, local_files_only=True)

        # 2. 원본 기본 모델을 로드합니다.
        model = AutoModelForSequenceClassification.from_pretrained(
            BASE_MODEL_PATH, 
            num_labels=len(id2label),
            id2label=id2label, 
            label2id=label2id, 
            trust_remote_code=True
        )

        # 3. 원본 모델의 단어 사전 크기를 새 토크나이저에 맞게 조절합니다.
        model.resize_token_embeddings(len(tokenizer))

        # 4. 크기가 조절된 모델 위에 학습된 LoRA 어댑터를 덮어씌웁니다.
        model = PeftModel.from_pretrained(model, FINETUNED_MODEL_PATH)
        
        # (선택사항) 추론 속도 향상을 위해 모델을 병합할 수 있습니다.
        # model = model.merge_and_unload()

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        print(f"[INFO] 모델 로드 완료. (Device: {device})")

    except Exception as e:
        print(f"[ERROR] 파인튜닝된 분류 모델 로드 실패: {e}")
        tokenizer, model = None, None

def contains_badword(content: str, badword_set: set) -> List[str]:
    if not isinstance(content, str):
        return []
    return [word for word in badword_set if re.search(r'\\b' + re.escape(word) + r'\\b', content)]

def run_exaone_batch(sentences: List[str]) -> List[Dict]:
    if not tokenizer or not model:
        return [{"label": "모델 로드 실패", "flag": False, "highlighted": [], "explanation": ["모델 로드 실패"]}] * len(sentences)

    results = []
    try:
        inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            predicted_ids = torch.argmax(outputs.logits, dim=-1)

        for i, sent in enumerate(sentences):
            pred_id = predicted_ids[i].item()
            label_name = model.config.id2label[pred_id]

            detected_badwords = contains_badword(sent, ALL_BADWORDS)
            if detected_badwords:
                label_name = "욕설"

            is_flagged = label_name != "문제 없음"
            highlighted = []

            if label_name == "욕설":
                highlighted = detected_badwords
            elif label_name in HIGHLIGHT_EXAMPLES:
                for hl in HIGHLIGHT_EXAMPLES[label_name]:
                    if hl in sent:
                        highlighted.append(hl)
                        break

            explanation = LABEL_EXPLANATIONS.get(label_name, "설명 없음")
            results.append({
                "label": label_name,
                "flag": is_flagged,
                "highlighted": highlighted,
                "explanation": [f"{label_name}: {explanation}"] if is_flagged else []
            })

    except Exception as e:
        print(f"[ERROR] 문장 분석 오류: {e}")
        return [{"label": "분석 오류", "flag": False, "highlighted": [], "explanation": ["분석 오류"]}] * len(sentences)

    return results

load_dependencies()

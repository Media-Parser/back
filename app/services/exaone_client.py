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
FINETUNED_MODEL_PATH = os.path.join(HOME_DIR, "ai", "finetuned_exaone")
PROMPT_TEMPLATE_FILE = os.path.join(HOME_DIR, "finetune", "prompt_definitions", "classification_prompt.txt")
SLANGS_FOLDER_PATH = os.path.join(HOME_DIR, "finetune", "slangs")

# --- 전역 변수 선언 ---
tokenizer = None
model = None
device = None
LABEL_EXPLANATIONS = {}
ALL_BADWORDS = set()

def load_dependencies():
    """
    모델, 토크나이저, 라벨 설명, 비속어 사전을 로드하는 함수.
    서버 시작 시 한 번만 실행됩니다.
    """
    global tokenizer, model, device, LABEL_EXPLANATIONS, ALL_BADWORDS
    
    # 1. 라벨 설명 로드
    try:
        LABEL_EXPLANATIONS = parse_labels_from_prompt_file(PROMPT_TEMPLATE_FILE)
        print("[INFO] 라벨 설명 로드 완료.")
    except Exception as e:
        print(f"[ERROR] 라벨 설명 로드 실패: {e}")

    # 2. 비속어 사전 로드 (욕설 하이라이팅에 사용)
    try:
        slang_csv_path = os.path.join(SLANGS_FOLDER_PATH, "slang.csv")
        lol_txt_path = os.path.join(SLANGS_FOLDER_PATH, "리그오브레전드_필터링리스트_2020.txt")

        with open(slang_csv_path, 'rb') as f:
            slang_encoding = chardet.detect(f.read())['encoding']
        with open(lol_txt_path, 'rb') as f:
            lol_encoding = chardet.detect(f.read())['encoding']

        slang_df = pd.read_csv(slang_csv_path, encoding=slang_encoding)
        with open(lol_txt_path, encoding=lol_encoding) as f:
            lol_words = set(line.strip() for line in f if line.strip())

        slang_words = set()
        for col in slang_df.columns:
            slang_words.update(slang_df[col].dropna().astype(str).str.strip())
        ALL_BADWORDS = slang_words | lol_words
        print(f"[INFO] 비속어 사전 로드 완료. (총 {len(ALL_BADWORDS)}개)")
    except Exception as e:
        print(f"[ERROR] 비속어 사전 로드 실패: {e}")

    # 3. 모델 및 토크나이저 로드
    if tokenizer is None or model is None:
        try:
            print(f"[INFO] 분류 모델 로드 중: {FINETUNED_MODEL_PATH}...")
            with open(os.path.join(FINETUNED_MODEL_PATH, "id2label.json"), 'r') as f:
                id2label = {int(k): v for k, v in json.load(f).items()}
            with open(os.path.join(FINETUNED_MODEL_PATH, "label2id.json"), 'r') as f:
                label2id = json.load(f)

            tokenizer = AutoTokenizer.from_pretrained(FINETUNED_MODEL_PATH, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                FINETUNED_MODEL_PATH, local_files_only=True, num_labels=len(id2label),
                id2label=id2label, label2id=label2id, trust_remote_code=True
            )
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            model.eval()
            print(f"[INFO] 모델 로드 완료. (Device: {device})")
        except Exception as e:
            print(f"[ERROR] 파인튜닝된 분류 모델 로드 실패: {e}")
            tokenizer, model = None, None

def contains_badword(content: str, badword_set: set) -> List[str]:
    """문장에서 비속어 사전에 있는 모든 단어를 찾아 리스트로 반환"""
    if not isinstance(content, str):
        return []
    # 정규표현식을 사용하여 단어 단위로 찾기
    found_words = [word for word in badword_set if re.search(r'\b' + re.escape(word) + r'\b', content)]
    return found_words

# 서버 시작 시 의존성 로드
load_dependencies()

def run_exaone_batch(sentences: List[str]) -> List[Dict]:
    """
    분류 모델을 사용하여 문장 목록을 분석하고, 프론트엔드 타입에 맞는 결과를 반환합니다.
    """
    if not tokenizer or not model:
        print("[ERROR] 모델이 로드되지 않았습니다.")
        return [{"flag": False, "highlighted": [], "explanation": ["모델 로드 실패"]}] * len(sentences)

    all_results = []
    
    try:
        inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True, max_length=128)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            predicted_ids = torch.argmax(outputs.logits, dim=-1)

        for i, sent in enumerate(sentences):
            pred_id = predicted_ids[i].item()
            label_name = model.config.id2label[pred_id]
            
            is_flagged = label_name != "문제 없음"
            explanation = LABEL_EXPLANATIONS.get(label_name, "설명 없음")
            highlighted_words = []

            # '욕설' 라벨일 경우, 비속어 사전을 이용해 하이라이트할 단어 찾기
            if label_name == "욕설":
                highlighted_words = contains_badword(sent, ALL_BADWORDS)

            # 그 외 라벨은 하이라이트 없음

            all_results.append({
                "flag": is_flagged,
                "highlighted": highlighted_words,
                "explanation": [explanation] if is_flagged else []
            })
            
    except Exception as e:
        print(f"[ERROR] 문장 분석 중 오류 발생: {e}")
        return [{"flag": False, "highlighted": [], "explanation": ["분석 오류"]}] * len(sentences)
        
    return all_results

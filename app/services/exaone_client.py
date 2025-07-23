# ✅ app/services/exaone_client.py
import torch
import os
import sys
import json
import re
import chardet
import pandas as pd
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

# 경로 설정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
services_dir = current_file_dir
app_dir = os.path.dirname(services_dir)
ssami_back_dir = os.path.dirname(app_dir)
ssami_dir = os.path.dirname(ssami_back_dir)
HOME_DIR = os.path.dirname(ssami_dir)
if HOME_DIR not in sys.path:
    sys.path.append(HOME_DIR) # sys.sys.path.append(HOME_DIR) 오타 수정 완료


from finetune.utils.prompt_parser import parse_labels_from_prompt_file

# 모델 경로 설정
FINETUNED_MODEL_PATH = os.path.join(HOME_DIR, "ai", "finetuned_exaone_v6") 
BASE_MODEL_PATH = os.path.join(HOME_DIR, "ai", "exaone_small")
PROMPT_TEMPLATE_FILE = os.path.join(HOME_DIR, "finetune", "prompt_definitions", "classification_prompt.txt")
SLANGS_FOLDER_PATH = os.path.join(HOME_DIR, "finetune", "slangs")
HIGHLIGHT_EXAMPLE_PATH = os.path.join(HOME_DIR, "finetune", "label_highlight_examples.json")

# 글로벌 변수
LABEL_EXPLANATIONS = {}
ALL_BADWORDS = set()
HIGHLIGHT_EXAMPLES = {}
tokenizer, model, device = None, None, None

def load_dependencies():
    global tokenizer, model, device, LABEL_EXPLANATIONS, ALL_BADWORDS, HIGHLIGHT_EXAMPLES

    print("[INFO] EXAONE 클라이언트 의존성 로딩 시작...")

    try:
        LABEL_EXPLANATIONS = parse_labels_from_prompt_file(PROMPT_TEMPLATE_FILE)
        # ✅ '욕설' 라벨에 대한 수동 설명 추가 제거. prompt_parser에 전적으로 의존.
        print("[INFO] 라벨 설명 로드 완료.")
        print(f"[INFO] 로드된 라벨 설명 키: {LABEL_EXPLANATIONS.keys()}")
    except Exception as e:
        print(f"[ERROR] 라벨 설명 로드 실패: {e}")
        raise RuntimeError(f"라벨 설명 로드 실패: {e}")

    try:
        slang_csv = os.path.join(SLANGS_FOLDER_PATH, "slang.csv")
        lol_txt = os.path.join(SLANGS_FOLDER_PATH, "리그오브레전드_필터링리스트_2020.txt")
        
        slang_df = pd.read_csv(slang_csv, encoding=chardet.detect(open(slang_csv, 'rb').read())['encoding'])
        with open(lol_txt, encoding=chardet.detect(open(lol_txt, 'rb').read())['encoding']) as f:
            lol_words = set(line.strip() for line in f if line.strip())
        slang_words = set()
        for col in slang_df.columns:
            slang_words.update(slang_df[col].dropna().astype(str).str.strip())
        ALL_BADWORDS = slang_words | lol_words
        print("[INFO] 비속어 사전 로드 완료.")
        print(f"[INFO] 로드된 비속어 수: {len(ALL_BADWORDS)}")
    except Exception as e:
        print(f"[ERROR] 비속어 사전 로드 실패: {e}")
        raise RuntimeError(f"비속어 사전 로드 실패: {e}")

    try:
        print(f"[INFO] 분류 모델 로드 중: {FINETUNED_MODEL_PATH}...")
        with open(os.path.join(FINETUNED_MODEL_PATH, "id2label.json"), 'r') as f:
            id2label = {int(k): v for k, v in json.load(f).items()}
        with open(os.path.join(FINETUNED_MODEL_PATH, "label2id.json"), 'r') as f:
            label2id = json.load(f)
        with open(HIGHLIGHT_EXAMPLE_PATH, 'r', encoding='utf-8') as f:
            HIGHLIGHT_EXAMPLES.update(json.load(f))
        print(f"[INFO] 로드된 HIGHLIGHT_EXAMPLES: {HIGHLIGHT_EXAMPLES.keys()}")

        tokenizer = AutoTokenizer.from_pretrained(FINETUNED_MODEL_PATH, local_files_only=True)
        # [START]/[END] 토큰 추가 로직은 train_model.py에서만.
        # 파인튜닝된 모델에 토크나이저가 저장될 때 이 토큰 정보도 함께 저장되므로 여기서 별도로 추가할 필요 없음
        # 만약 train_model.py에서 토크나이저에 스페셜 토큰을 추가했음에도 저장되지 않는다면 여기에 추가해야 함
        
        base_model = AutoModelForSequenceClassification.from_pretrained(
            BASE_MODEL_PATH, num_labels=len(id2label), id2label=id2label,
            label2id=label2id, trust_remote_code=True
        )
        base_model.resize_token_embeddings(len(tokenizer)) 
        model = PeftModel.from_pretrained(base_model, FINETUNED_MODEL_PATH)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        print(f"[INFO] 모델 로드 완료. (Device: {device})")
        print(f"[INFO] 모델의 id2label: {model.config.id2label}")
    except Exception as e:
        print(f"[ERROR] 파인튜닝된 분류 모델 로드 실패: {e}")
        tokenizer, model = None, None
        raise RuntimeError(f"분류 모델 로드 실패: {e}") 

def contains_badword(content: str, badword_set: set) -> List[str]:
    found_words = []
    if isinstance(content, str):
        for word in badword_set:
            if re.search(r'\b' + re.escape(word) + r'\b', content, re.IGNORECASE):
                found_words.append(word)
    return found_words

def run_exaone_batch(sentences: List[str]) -> List[Dict]:
    print(f"[DEBUG] run_exaone_batch 호출됨. 입력 문장 수: {len(sentences)}")
    if not tokenizer or not model:
        print("[ERROR] 모델이 로드되지 않았습니다. run_exaone_batch 종료.", file=sys.stderr)
        return [{"flag": False, "highlighted": [], "explanation": ["모델 로드 실패"]}] * len(sentences)

    all_results = []
    try:
        inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True, max_length=128)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        print(f"[DEBUG] 토크나이징 완료. 입력 ID Shape: {inputs['input_ids'].shape}")
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            predicted_ids = torch.argmax(logits, dim=-1)
        print(f"[DEBUG] 모델 추론 완료. 예측 ID: {predicted_ids.tolist()}")

        for i, sent in enumerate(sentences):
            pred_id = predicted_ids[i].item()
            label_name = model.config.id2label[pred_id]
            
            current_highlighted_list = []
            final_label_name = label_name 

            print(f"\n--- 문장 {i+1} 분석 시작 ---")
            print(f"[DEBUG] 원문: '{sent}'")
            print(f"[DEBUG] 모델 예측 라벨 ID: {pred_id}, 이름: '{label_name}'")

            # 1. 비속어 감지 (최우선 처리)
            detected_badwords = contains_badword(sent, ALL_BADWORDS)
            print(f"[DEBUG] 비속어 사전 감지 결과: {detected_badwords}")
            if detected_badwords:
                final_label_name = "부정적 표현" 
                current_highlighted_list = list(set(detected_badwords)) 
                print(f"[DEBUG] 비속어 감지! 최종 라벨 '{final_label_name}'로 강제 설정. 하이라이트: {current_highlighted_list}")
            else:
                # 2. 모델 예측 라벨이 '문제 없음'이 아닐 경우, 해당 라벨의 하이라이트 예시 확인
                if final_label_name != "문제 없음":
                    label_keywords = HIGHLIGHT_EXAMPLES.get(final_label_name, [])
                    for keyword in label_keywords:
                        if keyword in sent: 
                            current_highlighted_list.append(keyword)
                    current_highlighted_list = list(set(current_highlighted_list))
                    if current_highlighted_list:
                        print(f"[DEBUG] 모델 예측 라벨 '{final_label_name}'에 따른 하이라이트: {current_highlighted_list}")

            is_flagged = final_label_name != "문제 없음"
            
            # ✅ explanation 처리 로직 수정: 실제 설명을 가져와 라벨과 조합
            final_explanation_list = []
            if is_flagged:
                if detected_badwords and final_label_name == "부정적 표현":
                    # 비속어 감지로 '부정적 표현'이 된 경우 특정 설명을 사용
                    final_explanation_list.append("비속어 감지: 텍스트에 부적절한 표현이 포함되어 있습니다.")
                else:
                    # 모델 예측 라벨에 대한 설명을 LABEL_EXPLANATIONS에서 가져옴
                    explanation_from_map = LABEL_EXPLANATIONS.get(final_label_name)
                    # ✅ 라벨 이름과 설명을 조합하여 explanation 리스트에 추가
                    final_explanation_list.append(f"{final_label_name}: {explanation_from_map}")

            print(f"[DEBUG] 최종 is_flagged: {is_flagged}")
            print(f"[DEBUG] 최종 적용 라벨: '{final_label_name}'")
            print(f"[DEBUG] 최종 설명: '{final_explanation_list}'")
            print(f"[DEBUG] 최종 하이라이트 리스트: {current_highlighted_list}")

            all_results.append({
                "flag": is_flagged,
                "highlighted": current_highlighted_list,
                "explanation": final_explanation_list, # 수정된 explanation 리스트 사용
                "label": final_label_name # ✅ 최종 라벨 이름을 딕셔너리에 추가
            })
        print("\n[DEBUG] run_exaone_batch 모든 문장 처리 완료.")
        return all_results

    except Exception as e:
        print(f"[ERROR] 문장 분석 오류 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return [{"flag": False, "highlighted": [], "explanation": ["분석 오류"]}] * len(sentences)

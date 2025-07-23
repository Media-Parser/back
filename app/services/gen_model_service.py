# ✅ app/services/gen_model_service.py
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from app.services.prompt import build_prompt
from app.utils.parse import parse_generated_output
import sys
import torch
import os

# --- 경로 설정 ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
services_dir = current_file_dir
app_dir = os.path.dirname(services_dir)
ssami_back_dir = os.path.dirname(app_dir)
ssami_dir = os.path.dirname(ssami_back_dir)
HOME_DIR = os.path.dirname(ssami_dir)

if HOME_DIR not in sys.path:
    sys.path.append(HOME_DIR)

# --- 모델 경로 ---
MODEL_DIR = os.path.join(HOME_DIR, "ai", "finetuned_seq2seq_final_v3")
BASE_MODEL_NAME = "google/mt5-small"

# --- 디바이스 설정 ---
print(f"📱 현재 디바이스: {'cuda' if torch.cuda.is_available() else 'cpu'}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- 모델 로드 ---
try:
    # ✅ LoRA 학습 시 사용된 tokenizer 먼저 로드
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    print("📦 tokenizer 로드 완료")

    # ✅ base 모델 로드 후 tokenizer에 맞게 임베딩 재조정
    base_model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL_NAME)
    base_model.resize_token_embeddings(len(tokenizer))
    print(f"✅ base 모델 임베딩 재조정 완료: {base_model.get_input_embeddings().weight.shape}")

    # ✅ 병합된 state_dict 로드
    model_path = os.path.join(MODEL_DIR, "pytorch_model.bin")
    state_dict = torch.load(model_path, map_location="cpu")
    base_model.load_state_dict(state_dict, strict=False)
    print("✅ 병합된 state_dict 로드 완료")

    model = base_model.to(device)
    model.eval()
    print(f"✅ 모델 최종 준비 완료 (device: {device})")

except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    tokenizer = None
    model = None

# --- 추론 함수 ---
def analyze_with_generation(sentence: str):
    if tokenizer is None or model is None:
        return [{"label": "모델 로드 오류", "highlight": ""}]

    prompt = build_prompt(sentence)
    print("=" * 100)
    print(f"🖍️ 분석 문장: {sentence}")
    print(f"📟 프롬프트 길이: {len(prompt)}자 / 요약: {prompt.strip().splitlines()[-3:]}")

    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_length=256,
            num_beams=4,
            early_stopping=True
        )

    output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    print(f"\n📤 생성 결과 출력:\n{output_text}")

    parsed = parse_generated_output(output_text)
    print(f"\n📈 파싱 결과 객체:\n{parsed}")
    print("=" * 100 + "\n")

    return parsed

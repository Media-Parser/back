# ✅ app/services/prompt.py
import os
import sys

# --- 경로 설정 ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
services_dir = current_file_dir
app_dir = os.path.dirname(services_dir)
ssami_back_dir = os.path.dirname(app_dir)
ssami_dir = os.path.dirname(ssami_back_dir)
HOME_DIR = os.path.dirname(ssami_dir)

if HOME_DIR not in sys.path:
    sys.path.append(HOME_DIR)

def build_prompt(sentence: str) -> str:
    template_path = os.path.join(HOME_DIR, "finetune", "prompt_definitions", "classification_prompt.txt")
    with open(template_path, 'r', encoding='utf-8') as f:
        full_template = f.read()

    prefix, suffix = full_template.split('[분석 대상]')
    return f"{prefix.strip()}\n[분석 대상]\n{suffix.replace('{sentence}', sentence).strip()}"

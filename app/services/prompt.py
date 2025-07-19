# app/services/prompt.py
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build_prompt(sentence: str) -> str:
    template_path = os.path.join(BASE_DIR, "finetune", "prompt_definitions", "classification_prompt.txt")
    with open(template_path, 'r', encoding='utf-8') as f:
        full_template = f.read()

    prefix, suffix = full_template.split('[분석 대상]')
    return f"{prefix.strip()}\n[분석 대상]{suffix.strip().replace('{sentence}', sentence)}"
# app/services/gen_model_service.py
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from app.services.prompt import build_prompt
from app.utils.parse import parse_generated_output

import torch
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ai", "finetuned_seq2seq_final")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
model.eval()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

def analyze_with_generation(sentence: str):
    prompt = build_prompt(sentence)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    output_ids = model.generate(
        **inputs,
        max_length=256,
        num_beams=4,
        early_stopping=True
    )
    output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    parsed = parse_generated_output(output_text)
    return parsed
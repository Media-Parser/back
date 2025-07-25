from sklearn.metrics import classification_report
from typing import List, Dict

from app.utils.parse import parse_generated_output  # 필요시 경로 조정

def flatten_annotations(annotation_data: List[List[Dict[str, str]]]) -> List[str]:
    return [
        "문제 없음" if not anns or anns[0]["label"] == "문제 없음"
        else ", ".join(sorted(set(a["label"] for a in anns)))
        for anns in annotation_data
    ]

def evaluate_model(gold_annotations: List[List[Dict[str, str]]], predicted_outputs: List[str]):
    pred_annotations = [parse_generated_output(output) for output in predicted_outputs]

    gold_labels = flatten_annotations(gold_annotations)
    pred_labels = flatten_annotations(pred_annotations)

    print("🔍 정량 평가 (다중 라벨 텍스트 분류 기준)")
    print(classification_report(gold_labels, pred_labels, zero_division=0))
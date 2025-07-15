# service/node/05_generate/generate_suggestion_node.py

import os
import re
from typing import TypedDict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIError

# --- 환경 설정 및 클라이언트 초기화 ---
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
openai_client = OpenAI(api_key=api_key)


# --- 그래프 상태 정의 ---
class GraphState(TypedDict):
    question: str # 이제 이 노드에서는 사용되지 않지만, 상태 유지를 위해 남겨둠
    answer: str   # 이 노드의 핵심 입력값
    suggestion: Optional[str]


# --- 노드 함수 정의 ---
def generation_suggestion_node(state: GraphState) -> dict:
    """
    AI 자신의 답변(answer) 내용을 스스로 분석하여,
    사용자에게 도움이 될 만한 후속 작업(상세 설명, 요약, 표 정리 등)을 제안합니다.
    """
    print("--- 노드 실행: generation_suggestion_node ---")
    answer = state.get("answer")

    # AI의 답변 내용이 없으면 제안을 건너뜁니다.
    if not answer:
        print("경고: AI의 답변 내용이 없어 후속 작업 제안을 건너뜁니다.")
        return {"suggestion": "더 궁금한 점이 있으신가요?"}

    # === [핵심 수정] AI가 스스로의 답변을 보고 다음 행동을 제안하도록 프롬프트 변경 ===
    system_prompt = (
        "당신은 사용자와의 대화를 주도하는 '적극적인 AI 어시스턴트'입니다. "
        "당신이 방금 한 답변을 스스로 검토하고, 사용자가 흥미를 느낄 만한 유용한 다음 작업을 제안하는 역할을 합니다."
    )
    user_prompt = (
        f"AI인 제가 방금 아래와 같이 답변했습니다.\n\n"
        f"--- 제가 한 답변 내용 ---\n"
        f"{answer}\n"
        f"--- 여기까지 ---\n\n"
        f"이 답변 내용을 바탕으로, 제가 사용자를 위해 '다음에 해줄 수 있는 유용한 작업'을 제안해주세요.\n"
        f"제안의 종류는 다음과 같은 것들이 될 수 있습니다.\n"
        f"- 특정 키워드에 대한 '추가 상세 설명'\n"
        f"- 답변 내용에 기반한 '새로운 주제의 질문 생성'\n\n"
        f"사용자가 바로 선택하고 싶도록, 아래 예시처럼 간결한 형식으로 작성해주세요.\n"
        f"예시:\n"
        f"'민생 회복 정책'에 대해 더 자세히 설명해 드릴까요?\n"
    )

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # 이런 작업은 gpt-4o-mini 보다 gpt-4o-mini가 훨씬 더 잘합니다.
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=200
        )
        suggestion = completion.choices[0].message.content.strip()
        print(f"생성된 후속 작업 제안: \n{suggestion}")

    except APIError as e:
        print(f"오류: OpenAI API 호출 중 문제가 발생했습니다 - {e}")
        suggestion = "이 주제에 대해 더 자세히 알아볼까요?"
    except Exception as e:
        print(f"오류: 후속 작업 제안 중 알 수 없는 문제가 발생했습니다 - {e}")
        suggestion = "다른 도움이 필요하신가요?"

    return {"suggestion": suggestion}


# --- 독립적인 테스트를 위한 실행 코드 ---
if __name__ == '__main__':
    print("--- generation_suggestion_node.py 직접 실행 테스트 ---")

    test_state = GraphState(
        question="더불어민주당이 왜 물가대책 TF를 만들었어?", # 이 노드에서 직접 사용되지는 않음
        answer="더불어민주당은 최근 높아진 체감 물가와 중동 정세 불안에 따른 유가 상승 우려에 대응하여 민생 안정을 꾀하기 위해 물가대책 TF를 출범시켰습니다. 이를 통해 장단기 민생 회복 정책과 부동산 대책 등을 마련할 계획입니다.",
        suggestion=None
    )

    result_state = generation_suggestion_node(test_state)

    print("\n" + "="*50)
    print("--- 테스트 최종 결과 ---")
    print(f"AI의 기존 답변: {test_state['answer']}")
    print("-" * 20)
    print(f"✅ AI가 제안하는 다음 작업:\n{result_state['suggestion']}")
    print("="*50)
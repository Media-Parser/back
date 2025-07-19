import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, TypedDict, Optional
from langchain_core.documents import Document
# 다큐먼트가 이 다큐먼트가 아님. 수정해야하지만 일단 둘게요

# 제목 추천은 추천 모델 만들 거여서 맞추는 거 위주로
# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
# 설정된 환경 변수(OPENAI_API_KEY)를 자동으로 사용합니다.
client = OpenAI()

from graph_state import GraphState

def generate_titles(
    article_content: str,
    num_titles: int = 5,
    model: str = "gpt-4o-mini"
) -> Dict[str, List[str]]:
    """
    기사 본문을 기반으로 추천 제목 리스트를 JSON 형식으로 생성합니다.

    Args:
        article_content (str): 제목을 생성할 기사 본문 내용.
        num_titles (int): 생성할 제목의 개수.
        model (str): 사용할 OpenAI 모델.

    Returns:
        Dict[str, List[str]]: 'titles' 키에 제목 리스트를 담은 딕셔너리.
                                오류 발생 시 'error' 키에 메시지를 담아 반환.
    """
    # 💡 파싱에 용이하도록 AI에게 JSON 형식으로만 응답하도록 명확하게 지시합니다.
    system_prompt = """
    당신은 기사 내용을 분석하여 독자의 흥미를 끌 만한, 간결하고 핵심적인 제목을 생성하는 전문 카피라이터입니다.
    당신의 유일한 임무는 요청받은 내용을 바탕으로 제목 리스트를 JSON 형식으로 반환하는 것입니다.
    절대로 JSON 이외의 다른 설명이나 대화, 서론, 결론을 추가하지 마세요.
    """

    user_prompt = f"""
    아래 기사 내용을 바탕으로, 가장 매력적인 제목을 {num_titles}개 생성해 주세요.

    반드시 아래와 같은 JSON 형식으로만 응답해야 합니다:
    {{
      "titles": [
        "생성된 첫 번째 제목",
        "생성된 두 번째 제목",
        ...
      ]
    }}

    --- 기사 내용 ---
    {article_content}
    """

    try:
        completion = client.chat.completions.create(
            model=model,
            # 💡 OpenAI의 JSON 모드를 사용하여 응답 형식을 강제합니다.
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        response_content = completion.choices[0].message.content
        # OpenAI가 반환한 JSON 문자열을 파이썬 딕셔너리로 변환
        json_response = json.loads(response_content)

        # 응답 형식 검증
        if "titles" in json_response and isinstance(json_response["titles"], list):
            return json_response
        else:
            return {"error": "Invalid JSON format received from AI."}

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}
    
def generate_titles_node(state: GraphState) -> GraphState:
    """
    state에서 기사 본문을 추출하여 generate_titles 함수를 호출하고,
    결과를 state의 generation 필드에 맞게 변환하는 '연결용 노드'.
    """
    print("--- 노드 실행: generate_titles_node ---")
    context = state["selected_text"]
    print(context)

    title_result = generate_titles(article_content=context)

    if "error" in title_result:
        generation = f"제목 생성 중 오류가 발생했습니다: {title_result['error']}"
    else:
        # 생성된 제목들을 사용자가 보기 좋은 형식의 문자열로 변환
        formatted_titles = "\n".join([f"- {title}" for title in title_result.get("titles", [])])
        generation = f"추천 기사 제목은 다음과 같습니다.\n\n{formatted_titles}"

    # 그래프의 'generation' 상태를 업데이트하여 반환
    return {
        **state,
        "generation": generation,
        "apply_title": title_result.get("titles", [""])[0],  # 첫 번째 제목만
    }
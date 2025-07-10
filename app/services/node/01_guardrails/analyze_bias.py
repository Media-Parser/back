# service/node/01_guardrails/analyze_bias.py
import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_sentiment_bias(user_text):
    system_prompt = (
        "너는 감정 및 편향을 분석하는 언어 분석 전문가야.\n"
        "주어진 뉴스 문장 또는 사용자 발화의 감정(emotion)과 편향(bias)을 세개 미만의 어절으로 추출해줘.\n"
        "출력은 반드시 아래 형식처럼 해줘:\n"
        "- 감정: [감정 내용]\n"
        "- 편향: [편향 내용]\n\n"
        "가능한 감정 예시: 분노, 슬픔, 중립, 희망, 기쁨 등\n"
        "가능한 편향 예시: 정파적 공격, 중립, 과도한 일반화, 특정 집단 비난 등\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"\"{user_text.strip()}\""}
    ]

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    article = """더불어민주당은 이재명 정부의 협치 노력에 국민의힘이 호응하길 희망합니다. IMF 때보다 더한 고통에 그 어느 때보다 국가적 역량을 총집중해야 합니다. 
    하지만 국민의힘이 뼈를 깎는 쇄신은커녕 새 정부에 어깃장 놓을 궁리만 하며 당권 다툼에만 몰두하고 있어 실망스럽기 그지없습니다 그런데 반성과 쇄신은커녕 당권을 놓고 이전투구만 벌이고 있으니 기가 막힙니다. 국민의힘은 내란 수괴 윤석열을 배출한 것도 모자라 내란을 감싸다 국민의 심판을 받았습니다. 
     그런데 반성과 쇄신은커녕 당권을 놓고 이전투구만 벌이고 있으니 기가 막힙니다. 쇄신안은 내팽개치고 비대위원장 사퇴를 놓고 줄다리기 하는 게 국민의힘의 쇄신 방식입니까?
 더욱이 극우세력의 대변자를 자처해온 김문수 전 후보가 당권 도전에 나서겠다니 국민의힘은 도대체 어디로 갈 작정입니까?국민의힘이 쇄신을 거부하고 갈 길 바쁜 대한민국의 발목을 잡으려 한다면 국민께서 용서치 않으실 것입니다.
 """
    result = analyze_sentiment_bias(article)
    print("[감정/편향 분석 결과]")
    print(result)

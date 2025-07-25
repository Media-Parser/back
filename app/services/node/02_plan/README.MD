
## 🧠 Node: `plan_retrieval_node.py`

이 노드는 **LangGraph + LangChain Tool Calling**을 활용하여, 사용자의 질문을 분석하고 최적의 문서 검색 전략을 자동으로 생성하는 역할을 합니다.

---

### 🔧 기능 요약

* 사용자 질문을 기반으로 **검색 전략 (`strategy`)** 결정
* 필요한 **문서 유형 (`data_type`)** 분류 (기사, 논평 등)
* **검색용 질문 재작성 (`rewritten_question`)**
* **날짜/정당 필터 (`filters`)** 추출
* **요약/설명 생성 필요 여부 (`generation_required`)** 판단
* **본문 수정 필요 여부 (`apply_body_required`)** 판단

LangChain의 `Pydantic tool calling` 기능을 사용하여, GPT가 위 정보를 구조화된 JSON 형식으로 응답하도록 유도합니다.

---

### 🧩 기술 스택

* `LangGraph`: 상태 기반 LLM 그래프 흐름
* `LangChain`: LLM + Tool 호출 체인 구성
* `ChatOpenAI`: GPT-4o 모델 사용
* `Pydantic`: 응답 구조 정의
* `Tool Calling`: GPT가 직접 `RetrievalPlan` tool을 호출하여 응답 생성

---

### 📥 입력 상태 (`GraphState`)

```json
{
  "question": "각 당의 총선 공약을 비교해줘",
  "selected_text": "총선 공약",
  "use_full_document": false
}
```

---

### 📤 출력 상태 (`GraphState + plan`)

```json
{
  "plan": {
    "strategy": "balanced_retrieval",
    "data_type": ["opinion", "editorial"],
    "rewritten_question": "총선 공약 비교",
    "filters": {
      "startdate": "2024-07-25",
      "enddate": "2025-07-25",
      "party": ["더불어민주당", "국민의힘"]
    },
    "parameters": {
      "k": 10,
      "k_per_side": 5
    },
    "generation_required": true,
    "apply_body_required": false
  }
}
```

---

### 📌 전략 종류 (`strategy` 필드)

| 값                    | 설명                    |
| -------------------- | --------------------- |
| `standard_retrieval` | 일반 정보 탐색 목적           |
| `balanced_retrieval` | 정당 비교 등 균형 잡힌 관점 필요 시 |
| `title_generation`   | 콘텐츠 기반 제목 생성 요청       |
| `no_retrieval`       | 검색 없이 바로 답변 가능한 경우    |
| `no_generate`        | 부적절한 질문 등 처리 거부 필요 시  |

---

### ✅ 사용 예시

```python
from nodes.plan_retrieval_node import plan_retrieval_node

updated_state = plan_retrieval_node({
  "question": "후보별 공약 차이를 알려줘",
  "selected_text": "공약",
  "use_full_document": False
})
print(updated_state["plan"])
```


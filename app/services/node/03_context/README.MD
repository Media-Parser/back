## 💬 Node: `chat_history_node.py`

이 모듈은 LangGraph 기반 대화 시스템에서 **이전 대화 기록을 요약하거나 저장**하는 데 사용되는 노드입니다.  
대화 흐름을 더 정확하게 유지하고, 문맥 기반 응답 생성을 지원합니다.

---

### 1️⃣ `load_context_node`

#### ✅ 역할
사용자의 현재 질문에 대해, 이전 대화 기록 중 **관련 있는 부분만 요약**하여 context로 제공합니다.

#### ⚙️ 처리 방식
- `doc_id` 기준 최근 질문/응답 5개를 MongoDB에서 불러옵니다.
- `Q: ... / A: ...` 형식으로 정리 후, LLM에게 전달하여 요약합니다.
- LLM은 현재 질문과 **직접 관련된 정보만** 요약하여 반환합니다.

#### 📥 입력 예시 (`state`)
```json
{
  "doc_id": "doc_123",
  "question": "이전에 어떤 정책을 추천했었지?"
}
````

#### 📤 출력 예시 (`state["context"]`)

```json
{
  "context": "이전에 데이터 3법 관련 정책이 추천되었습니다."
}
```

---

### 2️⃣ `save_chathistory_node`

#### ✅ 역할

사용자의 질문, 생성된 응답, 적용 정보 등을 **MongoDB에 저장**하여 대화 히스토리를 유지합니다.

#### 🛠 저장 항목 예시

| 필드                          | 설명             |
| --------------------------- | -------------- |
| `doc_id`                    | 세션/문서 고유 ID    |
| `question`                  | 사용자 질문         |
| `generation`                | 생성된 응답         |
| `selected_text`             | 선택된 문장 (선택적)   |
| `suggestion`                | 추천 문장 (선택적)    |
| `apply_title`, `apply_body` | 실제 적용 여부 (선택적) |
| `value_type`                | 응답 유형 분류 (선택적) |

> 저장은 내부 `chat_service.py`의 `save_chat_qa()` 함수로 수행됩니다.

---

### ⚠️ 예외 처리

* `doc_id`가 없으면 저장을 건너뜁니다.
* MongoDB 저장 도중 오류 발생 시 콘솔에 로그 출력.

---

### 🧪 사용 예시

```python
from services.node.context.chat_history_node import load_context_node

state = {
  "doc_id": "doc_456",
  "question": "나 이 문서에서 뭐라고 물어봤지?"
}

updated_state = await load_context_node(state)
print(updated_state["context"])
```

---

### 📦 사용 기술

| 구성 요소                | 설명                     |
| -------------------- | ---------------------- |
| `ChatOpenAI`         | `gpt-4o-mini` 모델 사용    |
| `ChatPromptTemplate` | 질문-응답 기록을 요약하는 프롬프트 구성 |
| `MongoDB`            | 대화 히스토리 저장소            |
| `LangGraph`          | 노드 실행 흐름 관리            |
| `async/await`        | 비동기 처리 방식으로 응답 및 저장 수행 |

---

```

---

📌 이 마크다운을 `README.md` 내 적절한 위치에 붙여 넣으면 됩니다.  
만약 `Nodes` 또는 `Context Nodes`라는 섹션이 있다면 그 아래에 넣는 것을 권장드립니다.

원하시면 PR용 커밋 메시지 템플릿도 만들어 드릴 수 있습니다.
```

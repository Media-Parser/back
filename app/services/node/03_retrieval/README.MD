## 🔎 Node: `balanced_retrieval_node.py`

사용자의 질문을 바탕으로 **정당별로 균형 잡힌 문서 검색(balanced retrieval)**을 수행하는 LangGraph 노드입니다.  
특정 정당(예: "더불어민주당", "국민의힘") 각각에 대해 동일한 조건으로 벡터 기반 검색을 실행하고, 결과를 나누어 제공합니다.

---

### ✅ 주요 기능

| 항목 | 설명 |
|------|------|
| 🔄 정당별 검색 | 각 정당(party)에 대해 개별 검색 수행 |
| 📅 날짜 필터 | `startdate` ~ `enddate` 범위 필터 적용 |
| 📰 데이터 타입 필터 | `"editorial"`, `"opinion"`, `"news"` 중 선택적 필터링 |
| 💡 유사도 검색 | Chroma + OpenAI Embeddings 기반 벡터 검색 수행 |
| 🔁 결과 누적 | 각 정당별 검색 결과를 리스트로 누적 후 반환 |

---

### 🧠 사용되는 입력값 (`state["plan"]` 기반)

| 필드 | 설명 |
|------|------|
| `rewritten_question` | 검색용으로 재작성된 질문 |
| `parameters.k_per_side` | 정당당 검색할 문서 개수 (기본 2) |
| `filters.party` | 검색 대상 정당 리스트 (기본값: ["더불어민주당", "국민의힘"]) |
| `filters.startdate/enddate` | 날짜 필터 (`YYYY-MM-DD` 형식) |
| `data_type` | 문서 유형 필터 (`editorial`, `opinion`, `news`) |

---

### 📦 기술 스택

- **LangChain**: Chroma 벡터스토어 + OpenAI Embedding
- **Chroma**: `similarity_search_with_relevance_scores()`로 유사도 + 필터 기반 검색
- **LangGraph**: 노드 실행 흐름 관리
- **환경 변수**: `.env`에서 OpenAI 키 로딩

---

### 🧾 출력 예시 (`state["documents_by_party"]`)

```json
[
  {
    "party": "더불어민주당",
    "documents": [
      {
        "page_content": "...",
        "metadata": { "date": "2024-03-10", "data_type": "opinion" }
      }
    ]
  },
  {
    "party": "국민의힘",
    "documents": [
      {
        "page_content": "...",
        "metadata": { "date": "2024-03-11", "data_type": "opinion" }
      }
    ]
  }
]
````

---

### ⚠️ 예외 처리

* 날짜 파싱 실패 시 자동으로 무시
* 벡터스토어 검색 중 오류 발생 시 콘솔 출력 (각 정당별로 독립적으로 수행되므로 실패해도 전체는 계속됨)

---

### 🔍 로그 출력 예시

```
--- 노드 실행: 2b. balanced_retrieval ---
🔍 [정당: 더불어민주당] 검색 필터: {'$and': [{'date_int': {'$gte': 20240701}}, {'party': {'$eq': '더불어민주당'}}]}
✅ 더불어민주당: 2개 검색됨
🔍 [정당: 국민의힘] 검색 필터: {'$and': [{'date_int': {'$gte': 20240701}}, {'party': {'$eq': '국민의힘'}}]}
✅ 국민의힘: 2개 검색됨
```

---

### 🧪 실행 흐름 예시

```python
from nodes.balanced_retrieval_node import balanced_retrieval_node

state = {
  "plan": {
    "rewritten_question": "총선 공약 비교",
    "filters": {
      "party": ["더불어민주당", "국민의힘"],
      "startdate": "2024-07-01",
      "enddate": "2024-07-25"
    },
    "parameters": { "k_per_side": 2 },
    "data_type": ["opinion"]
  }
}

new_state = balanced_retrieval_node(state)
print(new_state["documents_by_party"])
```


## 🧠 Node: `grade_and_filter_node.py`

사용자의 질문에 대한 검색 결과 문서를 GPU 기반 **Cross-Encoder 리랭커**로 정밀하게 평가하고, **청크 단위로 필터링**하는 노드입니다.  
검색 결과의 품질을 높이고, LLM 응답 생성 단계에서 최적의 문서를 제공하는 데 사용됩니다.

---

### ✅ 주요 기능 요약

| 단계 | 설명 |
|------|------|
| 📥 문서 정제 | 기존 문서 리스트에서 점수 제거 (Tuple → Document) |
| 📦 문서 청킹 | 300자 기준으로 청크로 나눔 (겹침 50자) |
| 🎯 GPU 리랭크 | KoBGE 기반 Cross-Encoder로 문서 청크를 질문과 정밀 비교 |
| 🔗 요약 생략 시 링크 목록 생성 | 요약이 필요 없는 경우, 문서 하이퍼링크만 출력 |
| 🔁 문서 전달 | 생성이 필요한 경우 Top 문서들을 다음 노드로 전달 |

---

### 🧠 사용 모델

- 모델: [`Dongjin-kr/ko-reranker`](https://huggingface.co/Dongjin-kr/ko-reranker)  
- 구조: BERT 기반 Cross-Encoder
- 실행: `transformers` + `torch` 사용 (GPU 또는 CPU)

```python
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
````

---

### ⚙️ 입력/출력 예시

#### 📥 입력 (`state`)

```json
{
  "question": "총선에서 각 당의 입장은 어떻게 다른가요?",
  "documents": [Document(page_content="...", metadata={"title": "민주당 입장", ...})],
  "plan": {
    "generation_required": false
  }
}
```

#### 📤 출력 (`state`)

```json
{
  "documents": [...Top 5 문서 청크...],
  "generation": "- [민주당 입장](https://example.com/1)\n- [국민의힘 입장](https://example.com/2)"
}
```

> `generation_required: false`인 경우 `generation` 필드에 링크 요약 반환
> 그렇지 않으면 문서만 다음 노드로 전달됨

---

### 📊 로그 예시

```
--- 노드 실행: 3. grade_and_filter (GPU 리랭커 + 청킹) ---
📥 총 12개 문서 리랭킹 중...
✅ 1위 문서 (score=0.4721): 국민의힘은 복지 재원 확보를 위해...
🎯 최종 선택 문서 조각 수: 5
```

---

### 📦 구성 요소별 기술 스택

| 구성 요소      | 라이브러리                                        |
| ---------- | -------------------------------------------- |
| 문서 청킹      | `RecursiveCharacterTextSplitter` (LangChain) |
| 리랭커 모델     | `transformers` + `torch`                     |
| 벡터 정규화     | `exp_normalize()` 기반 softmax                 |
| 멀티 디바이스 지원 | CUDA / CPU 자동 선택                             |
| 문서 요약 대체   | Markdown 링크 텍스트로 출력                          |

---

### 🧪 사용 예시 (직접 호출)

```python
from services.node.03_retrieval.grade_and_filter_node import grade_and_filter_node

state = {
  "question": "총선 공약 차이를 비교해줘",
  "documents": [...],  # Document 리스트
  "plan": { "generation_required": False }
}

result = grade_and_filter_node(state)
print(result["generation"])  # → 문서 링크 리스트 또는 다음 노드로 전달
```


아래는 `standard_retrieval_node.py`를 설명하는 GitHub `README.md`용 **마크다운 문서**입니다. 이 노드는 **기본 유사도 기반 문서 검색 기능**을 수행하는 LangGraph 노드로, 날짜/주제 필터와 함께 Chroma DB를 순회하며 문서를 검색하는 구조입니다.




## 📄 Node: `standard_retrieval_node.py`

이 노드는 사용자의 질문을 기반으로, 설정된 메타데이터 필터(날짜, 주제 등)를 적용하여 **Chroma 벡터 데이터베이스에서 유사 문서를 검색**하는 기능을 수행합니다.

---

### ✅ 주요 기능 요약

| 항목 | 설명 |
|------|------|
| 🔎 재작성 질문 기반 검색 | `plan.rewritten_question` 기준 유사도 검색 수행 |
| 📅 날짜 필터 지원 | `startdate`, `enddate` → `date_int`로 변환 |
| 🧠 토픽 필터 지원 | 특정 주제 ID로 필터링 (`topic_id`) |
| 🗂️ 데이터 타입별 검색 | `"opinion"`, `"editorial"` 등 유형별 DB에서 검색 |
| 📊 유사도 점수 포함 | `similarity_search_with_relevance_scores()` 사용 |
| 🎯 최종 문서 정렬 | 점수 기준 정렬 후 상위 `k`개 추출 |

---

### 🧠 입력 (`state`)

```json
{
  "plan": {
    "rewritten_question": "총선 공약 비교",
    "parameters": { "k": 10 },
    "filters": {
      "startdate": "2024-06-01",
      "enddate": "2024-07-25",
      "topic_id": "election"
    },
    "data_type": ["opinion", "editorial"]
  }
}
````

---

### 📤 출력 (`state["documents"]`)

최종 선택된 문서 리스트 (LangChain `Document` 객체 배열).
예시:

```json
[
  {
    "page_content": "...총선 공약에 대한 더불어민주당의 입장...",
    "metadata": {
      "date": "2024-07-01",
      "topic_id": "election",
      "data_type": "opinion"
    }
  },
  ...
]
```

---

### 🔎 로그 출력 예시

```
--- 노드 실행: standard_retrieval (유사도 점수 포함) ---
🔍 검색 필터: {'$and': [{'date_int': {'$gte': 20240601}}, {'date_int': {'$lte': 20240725}}, {'topic_id': {'$eq': 'election'}}]}
📁 검색 대상 DB: chroma_db_opinion
📁 검색 대상 DB: chroma_db_editorial
📦 최종 문서 개수: 6

📄 문서 1 (score: 0.7621)
내용: 더불어민주당은 이번 총선에서 복지 재정 확대를 주요 공약으로 내세웠다...
메타데이터: {'date': '2024-07-01', 'data_type': 'opinion', ...}
```

---

### 📦 기술 스택

| 구성 요소              | 설명                                |
| ------------------ | --------------------------------- |
| `Chroma`           | 유사도 기반 벡터 검색                      |
| `OpenAIEmbeddings` | 문장 임베딩 생성                         |
| `date_to_int`      | `"YYYY-MM-DD"` → `YYYYMMDD` 정수 변환 |
| `GraphState`       | LangGraph 흐름 상태 객체                |

---

### ⚠️ 예외 처리

* 날짜나 필터값 누락 시 해당 조건 생략
* 각 데이터 타입별 DB 검색 중 오류 발생 시 개별 출력 (전체 중단 없음)

---

### 🧪 실행 예시

```python
from services.node.03_retrieval.standard_retrieval_node import standard_retrieval_node

state = {
  "plan": {
    "rewritten_question": "후보자 공약 비교",
    "filters": {
      "startdate": "2024-06-01",
      "enddate": "2024-07-01",
      "topic_id": "총선"
    },
    "parameters": { "k": 5 },
    "data_type": ["opinion"]
  }
}

updated_state = standard_retrieval_node(state)
print(updated_state["documents"][0].page_content[:200])
```
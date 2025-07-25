import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from chromadb import PersistentClient
from bertopic import BERTopic
from app.core.config import Settings
import numpy as np
from tqdm import tqdm
from app.utils.tokenizer import bertopic_tokenizer
import builtins

# tokenizer 설정
builtins.bertopic_tokenizer = bertopic_tokenizer

# BERTopic 모델 로드
topic_model = BERTopic.load("/home/ubuntu/ssami/ssami-back/my_bertopic_model_fixed")

# 여러 ChromaDB 경로
db_paths = [
    "/home/ubuntu/ssami/ssami-back/chroma_db_editorial",
    "/home/ubuntu/ssami/ssami-back/chroma_db_news",
    "/home/ubuntu/ssami/ssami-back/chroma_db_opinion"
]

BATCH_SIZE = 100

for db_path in db_paths:
    print(f"\n📂 Processing DB: {db_path}")
    client = PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="langchain")

    docs = collection.get(include=["documents", "metadatas", "embeddings"])  # ✅ embeddings 포함
    documents, metadatas, ids, embeddings = (
        docs["documents"], docs["metadatas"], docs["ids"], docs["embeddings"]
    )

    # 필터: topic_id 없는 문서만 (index도 함께 보존)
    filtered = [
        (i, doc, meta, doc_id, embedding)
        for i, (doc, meta, doc_id, embedding) in enumerate(zip(documents, metadatas, ids, embeddings))
        if "topic_id" not in meta
    ]

    print(f"🔍 대상 문서 수: {len(filtered)}")

    for i in tqdm(range(0, len(filtered), BATCH_SIZE)):
        batch = filtered[i:i+BATCH_SIZE]
        batch_docs = [doc for _, doc, _, _, _ in batch]
        batch_embeddings = [embedding for _, _, _, _, embedding in batch]

        try:
            topics, _ = topic_model.transform(batch_docs, embeddings=np.array(batch_embeddings))
        except Exception as e:
            print(f"❌ 오류 발생 (배치 {i}): {e}")
            continue

        batch_ids = []
        batch_metas = []
        for j, (_, doc, meta, doc_id, _) in enumerate(batch):
            topic_id = int(topics[j]) if topics[j] != -1 else -1
            meta["topic_id"] = topic_id
            batch_ids.append(doc_id)
            batch_metas.append(meta)

        collection.update(ids=batch_ids, metadatas=batch_metas)

    print(f"✅ Done: {db_path} ({len(filtered)} 문서 처리 완료)")

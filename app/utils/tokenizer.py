# app/utils/tokenizer.py

from konlpy.tag import Okt

# Okt 객체 생성 (한 번만)
okt = Okt()

# 한국어 불용어 리스트
korean_stopwords = {
    '것', '수', '때', '곳', '중', '안', '밖', '위', '아래', '앞', '뒤', '옆',
    '이것', '그것', '저것', '여기', '거기', '저기', '이곳', '그곳', '저곳',
    '등', '및', '통해', '위해', '대해', '관해',
    '오늘', '어제', '내일', '지금', '현재', '과거', '미래',
    '사람', '사람들', '모든', '각각', '전체', '부분',
    '더', '같은', '이번', '이번에', '우리', '여러분', '자유', '정신',
    '대한민국', '대통령', '후보', '대표', '의원', '정부'
}

def tokenize_ko(text: str) -> list[str]:
    """
    우선 명사를 추출하고, 없을 경우 형태소 단위로 토큰화
    """
    tokens = okt.nouns(text)
    if not tokens:
        tokens = okt.morphs(text)
    return tokens

def bertopic_tokenizer(text: str) -> list[str]:
    """
    명사/형용사/동사 추출 후 불용어 제거
    """
    noun_or_morph_tokens = set(tokenize_ko(text))
    pos_filtered_tokens = set(
        word for word, pos in okt.pos(text)
        if pos in {'Noun', 'Adjective', 'Verb'}
        and len(word) > 1
        and word not in korean_stopwords
    )
    return list(noun_or_morph_tokens & pos_filtered_tokens)

# 불용어 목록도 외부에서 쓸 수 있게 export
__all__ = ["bertopic_tokenizer", "korean_stopwords"]

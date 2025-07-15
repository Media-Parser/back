# node/__init__.py
import importlib
from .graph_state import GraphState

# Plan
plan_module = importlib.import_module('.02_plan.plan_retrieval_node', package=__name__)
plan_retrieval_node = plan_module.plan_retrieval_node


balanced_module = importlib.import_module('.03_retrieval.balanced_retrieval_node', package=__name__)
balanced_retrieval_node = balanced_module.balanced_retrieval_node

grade_module = importlib.import_module('.03_retrieval.grade_and_filter_node', package=__name__)
grade_and_filter_node = grade_module.grade_and_filter_node

standard_module = importlib.import_module('.03_retrieval.standard_retrieval_node', package=__name__)
standard_retrieval_node = standard_module.standard_retrieval_node

# Generate
generate_module = importlib.import_module('.05_generate.generate_node', package=__name__)
# 해당 모듈에서 'generate_node' 함수를 가져옵니다.
generate_response_node = generate_module.generate_response_node

# --- Title Generation Node 임포트 ---
# '.05_generate.title_generator_node' 모듈을 동적으로 불러옵니다.
title_generator_module = importlib.import_module('.05_generate.generate_title_node', package=__name__)
# 해당 모듈에서 'generate_titles' 함수를 가져옵니다.
generate_titles_node = title_generator_module.generate_titles_node

suggestion_generater_module = importlib.import_module('.05_generate.generate_suggestion_node', package=__name__)
generate_suggestion_node = suggestion_generater_module.generation_suggestion_node  # 이름을 맞춰줌

__all__ = [
    'GraphState',
    'plan_retrieval_node',
    'balanced_retrieval_node',
    'grade_and_filter_node',
    'standard_retrieval_node',
    'create_prompt_messages',
    'generate_suggestion_node',
    'generate_titles_node',
]
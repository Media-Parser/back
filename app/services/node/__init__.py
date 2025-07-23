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


# 모듈 경로 지정 (상대경로로 03_context 폴더 내부의 chat_history_node.py)
context_module = importlib.import_module('03_context.chat_history_node')

# 노드 함수 불러오기
load_context_node = getattr(context_module, 'load_context_node')
#save_context_node = getattr(context_module, 'save_context_node')
#load_chathistory_node = getattr(context_module, 'load_chathistory_node')
save_chathistory_node = getattr(context_module, 'save_chathistory_node')

# --- Title Generation Node 임포트 ---
# '.05_generate.title_generator_node' 모듈을 동적으로 불러옵니다.
title_generator_module = importlib.import_module('.05_generate.generate_title_node', package=__name__)
# 해당 모듈에서 'generate_titles' 함수를 가져옵니다.
generate_titles_node = title_generator_module.generate_titles_node

main_generater_module = importlib.import_module('.05_generate.generate_main_node', package=__name__)
generate_main_node = main_generater_module.generate_main_node  # 이름을 맞춰줌
__all__ = [
    'GraphState',
    'plan_retrieval_node',
    'balanced_retrieval_node',
    'grade_and_filter_node',
    'standard_retrieval_node',
    'create_prompt_messages',
    'generate_titles_node',
    'generate_main_node',
    'save_chathistory_node',
    #'load_chathistory_node',
    'load_context_node',
    #'save_context_node'
]
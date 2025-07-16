# test.py

import torch
print("CUDA 사용 가능:", torch.cuda.is_available())  # True가 나와야 정상
print("GPU 개수:", torch.cuda.device_count())       # 보통 1개
print("현재 디바이스:", torch.cuda.current_device())
print("GPU 이름:", torch.cuda.get_device_name(0))
# app/services/hwpx_extractor.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JAR_PATH = os.path.join(BASE_DIR, "python-hwpxlib-main", "hwpxlib-1.0.5.jar")
LOADER_PATH = os.path.join(BASE_DIR, "python-hwpxlib-main", "hwpx_loader.py")

def extract_text_from_hwpx(file_bytes: bytes) -> str:
    import tempfile
    import subprocess

    with tempfile.NamedTemporaryFile(delete=False, suffix=".hwpx") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as out_tmp:
        out_path = out_tmp.name

    try:
        # 1. text=True, encoding="utf-8" 제거!
        result = subprocess.run(
            ["python", LOADER_PATH, "--hwpx_jar_path", JAR_PATH, "--file_path", tmp_path, "--output", out_path],
            capture_output=True
        )
        # 2. 실패시 stderr만 "바이트로" 출력(참고)
        if result.returncode != 0:
            print("[extract_text_from_hwpx] 에러: ", result.stderr.decode('utf-8', errors='replace'))
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
        # 3. 결과 파일만 utf-8로 읽기
        with open(out_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        os.remove(tmp_path)
        os.remove(out_path)
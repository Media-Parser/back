# app/services/hwp_extractor.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JAR_PATH = os.path.join(BASE_DIR, "python-hwplib-main", "hwplib-1.1.8.jar")
LOADER_PATH = os.path.join(BASE_DIR, "python-hwplib-main", "hwp_loader.py")

# print("LOADER_PATH:", LOADER_PATH)
# print("JAR_PATH:", JAR_PATH)

def extract_text_from_hwp(file_bytes: bytes) -> str:
    import tempfile
    import subprocess

    with tempfile.NamedTemporaryFile(delete=False, suffix=".hwp") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as out_tmp:
        out_path = out_tmp.name

    try:
        result = subprocess.run(
            ["python3", LOADER_PATH, "--hwp_jar_path", JAR_PATH, "--file_path", tmp_path, "--output", out_path],
            capture_output=True
        )
        if result.returncode != 0:
            print("[extract_text_from_hwp] 에러: ", result.stderr.decode('utf-8', errors='replace'))
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
        with open(out_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        os.remove(tmp_path)
        os.remove(out_path)
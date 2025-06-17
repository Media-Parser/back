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

    try:
        result = subprocess.run(
            ["python", LOADER_PATH, "--hwpx_jar_path", JAR_PATH, "--file_path", tmp_path],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        return result.stdout
    finally:
        os.remove(tmp_path)


# 테스트 코드
# if __name__ == "__main__":
#     filename = os.path.join(
#         BASE_DIR,
#         "python-hwpxlib-main",
#         "2023년 디지털정부 발전유공 포상 추진계획.hwpx"
#     )
#     with open(filename, "rb") as f:
#         file_bytes = f.read()
#     text = extract_text_from_hwpx(
#         file_bytes=file_bytes
#     )
#     print(text)


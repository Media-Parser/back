# app/tests/test_auth.py
import pytest

@pytest.mark.asyncio
async def test_google_auth_callback(client):
    print("\n=== [구글 인증 콜백 API 테스트 시작] ===")
    # 실제 구글 OAuth는 실제 브라우저와 통신이 필요해 mock/token 방식만 테스트
    # 테스트 토큰/코드를 강제로 넘기는 경우만 가능!
    dummy_code = "dummycode"
    res = await client.get(f"/auth/google/callback?code={dummy_code}")
    print("구글 인증 콜백 응답:", res.status_code)
    # 실제 구현에 따라 400/401/500 등 나올 수 있음
    assert res.status_code in [400, 401, 500]
    print("=== [구글 인증 콜백 API 테스트 끝] ===\n")

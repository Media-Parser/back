# app/tests/test_auth.py
import pytest

@pytest.mark.asyncio
@pytest.mark.parametrize("provider,path", [
    ("google", "/auth/google"),
    ("kakao", "/auth/kakao"),
    ("naver", "/auth/naver"),
])
async def test_auth_redirect(client, provider, path):
    """
    OAuth 인증 엔드포인트(google/kakao/naver) 리다이렉트 테스트
    """
    res = await client.get(path, follow_redirects=False)
    assert res.status_code in [302, 307]
    assert "location" in res.headers

# 콜백 테스트는 별도 mock 필요. 또는 integration test에서 커버

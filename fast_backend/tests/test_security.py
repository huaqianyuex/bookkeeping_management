"""utils.security 单元测试 — 密码哈希 / JWT / LIKE 转义"""

from datetime import timedelta

import jwt
import pytest

from utils.security import (
    create_access_token,
    decode_access_token,
    escape_like,
    hash_password,
    verify_password,
)


class TestPassword:
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("s3cret-密码")
        assert hashed.startswith("$2a$")  # 兼容旧 Spring BCrypt 前缀
        assert verify_password("s3cret-密码", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_verify_malformed_hash_returns_false(self):
        """坏哈希不应抛异常，直接返回 False"""
        assert verify_password("x", "not-a-bcrypt-hash") is False


class TestJwt:
    def test_roundtrip(self):
        token = create_access_token(42)
        payload = decode_access_token(token)
        assert payload["sub"] == "42"

    def test_expired_token_rejected(self):
        token = create_access_token(1, expires_delta=timedelta(seconds=-10))
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_tampered_signature_rejected(self):
        token = create_access_token(1)
        with pytest.raises(jwt.InvalidSignatureError):
            decode_access_token(token[:-3] + "abc")


class TestEscapeLike:
    def test_escapes_meta_characters(self):
        assert escape_like("100%") == "100\\%"
        assert escape_like("a_b") == "a\\_b"
        assert escape_like("a\\b") == "a\\\\b"

    def test_empty_and_plain(self):
        assert escape_like("") == ""
        assert escape_like("普通关键词") == "普通关键词"

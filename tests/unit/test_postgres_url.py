import ssl

from app.config import normalize_postgres_url


def test_strips_sslmode_and_uses_ssl_context_for_require():
    raw = (
        "postgresql://doadmin:secret@db.example.com:25060/defaultdb?sslmode=require"
    )
    url, connect_args = normalize_postgres_url(raw)

    assert "sslmode" not in url
    assert url.startswith("postgresql+asyncpg://")
    ctx = connect_args["ssl"]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ctx.check_hostname is False


def test_postgres_scheme_normalized():
    raw = "postgres://user:pass@host:5432/mydb?sslmode=require"
    url, connect_args = normalize_postgres_url(raw)

    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert isinstance(connect_args["ssl"], ssl.SSLContext)


def test_no_sslmode_means_no_connect_args():
    raw = "postgresql://user:pass@localhost:5432/mydb"
    url, connect_args = normalize_postgres_url(raw)

    assert connect_args == {}
    assert "postgresql+asyncpg://" in url

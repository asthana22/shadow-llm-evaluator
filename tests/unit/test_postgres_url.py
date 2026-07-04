from app.config import normalize_postgres_url


def test_strips_sslmode_and_enables_ssl():
    raw = (
        "postgresql://doadmin:secret@db.example.com:25060/defaultdb?sslmode=require"
    )
    url, connect_args = normalize_postgres_url(raw)

    assert "sslmode" not in url
    assert url.startswith("postgresql+asyncpg://")
    assert connect_args == {"ssl": True}


def test_postgres_scheme_normalized():
    raw = "postgres://user:pass@host:5432/mydb?sslmode=require"
    url, connect_args = normalize_postgres_url(raw)

    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert connect_args["ssl"] is True


def test_no_sslmode_means_no_connect_args():
    raw = "postgresql://user:pass@localhost:5432/mydb"
    url, connect_args = normalize_postgres_url(raw)

    assert connect_args == {}
    assert "postgresql+asyncpg://" in url

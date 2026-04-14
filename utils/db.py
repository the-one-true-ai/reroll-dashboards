"""
Database connection and query helper.

Credentials are loaded from Streamlit secrets (cloud) or environment variables (local).
All queries are cached for 1 hour — call st.cache_data.clear() to force a refresh.
"""

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


def _get_secret(key: str) -> str:
    """Read from st.secrets if available, else fall back to environment variable."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        value = os.environ.get(key, "")
        if not value:
            raise RuntimeError(
                f"Missing credential: {key}. "
                "Set it in .streamlit/secrets.toml (local) or Streamlit Cloud secrets."
            )
        return value


@st.cache_resource
def _engine():
    host = _get_secret("ANALYTICS_HOST")
    user = _get_secret("ANALYTICS_USER")
    password = _get_secret("ANALYTICS_PASSWORD")
    dbname = _get_secret("ANALYTICS_DBNAME")
    url = f"postgresql+psycopg://{user}:{password}@{host}:5432/{dbname}?sslmode=require"
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    """Execute SQL against the analytics database and return a DataFrame."""
    with _engine().connect() as conn:
        return pd.read_sql(text(sql), conn)

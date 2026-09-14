from __future__ import annotations

import streamlit as st
from core.models import Settings
from core.converter import Converter
from environment.locks import OPERATION_LOCK

@st.cache_resource(max_entries=2, show_spinner=False)
def get_converter(settings: Settings, environment_revision: str = '') -> Converter:
    # A completed setup changes the cache key so new Tesseract paths are applied.
    with OPERATION_LOCK:
        return Converter(settings)

"""Streamlit entry point: compose independently maintained UI panels."""
import streamlit as st
from ui.theme import configure_page, render_header
from ui.settings_panel import render_settings
from ui.input_panel import render_inputs
from ui.batch_panel import render_batch
from ui.result_panel import render_results
from environment_ui import render_environment_panel


def main():
    configure_page()
    settings = render_settings()
    render_header()
    render_batch(settings, *render_inputs())
    render_results()
    st.divider()
    render_environment_panel()


if __name__ == "__main__":
    main()

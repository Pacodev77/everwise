# ui/components/campus_cards.py

import streamlit as st
from ui.charts.donut_estado import donut_estado

def campus_card(nombre: str, valor: float):
    with st.container():
        st.markdown(
            f"""
            <div class="campus-card-elite">
                <div class="campus-title">{nombre}</div>
            """,
            unsafe_allow_html=True
        )

        st.altair_chart(
            donut_estado(valor),
            use_container_width=True
        )

        st.markdown("</div>", unsafe_allow_html=True)

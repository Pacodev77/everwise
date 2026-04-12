# ui/sections/footer.py
import streamlit as st
import datetime

def render_footer(ciclo_seleccionado=None):
    if ciclo_seleccionado is None:
        ciclo_seleccionado = datetime.datetime.now().year
        
    st.markdown("---")
    st.markdown(f"""
        <div style="text-align:center;color:#94a3b8;font-size:0.85rem;padding:20px 0;">
            Everwise ® Grow wiser every day<br>
            designed by Paco Ruiz · Copyright © · {ciclo_seleccionado}
        </div>
    """, unsafe_allow_html=True)

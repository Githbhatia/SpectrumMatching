import streamlit as st

st.logo("HXBLogo.png", size="large")
main_page= st.Page("SingleComponentMatching.py", title="Single Component Spectrum Matching", icon=":material/home:")
create_page = st.Page("TwoComponentMatching.py", title="Two Component Spectrum Matching", icon=":material/add_circle:")
pg = st.navigation([main_page,create_page])
st.set_page_config(page_title="Spectrum Matching", page_icon=":material/edit:")
pg.run()

import streamlit as st

st.title("🧠 Multi-Agent Research Assistant")

query=st.text_input("Enter your research topic")

if st.button("Generate Research Plan"):
   st.write(f"Research topic: {query}")

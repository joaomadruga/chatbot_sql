import os
import streamlit as st
from helpers import natural_language_to_sql
from streamlit_chat import message
from dotenv import load_dotenv

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

st.set_page_config(
    page_title="Natural Language to SQL",
    page_icon=":robot:"
)
st.header("Natural Language to SQL")

if 'list_of_messages' not in st.session_state:
    st.session_state['list_of_messages'] = []

question = st.chat_input()
if question:
    st.session_state['list_of_messages'].append([question, True])
    st.session_state['list_of_messages'].append([natural_language_to_sql(question)['output'], False])

if st.session_state['list_of_messages']:
    for i, each_question in enumerate(st.session_state['list_of_messages']):
        current_question, is_user = each_question
        message(current_question, key=str(i), is_user=is_user)

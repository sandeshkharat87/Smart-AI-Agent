import gradio as gr
from graph import chat


gr.ChatInterface(chat, type="messages").launch()
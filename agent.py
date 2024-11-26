import re
from langgraph.graph import StateGraph, START, END, add_messages
from typing_extensions import TypedDict, Annotated
from langchain_ollama.chat_models import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import PromptTemplate
from termcolor import colored
from langchain_core.tools import tool
import subprocess
from langchain_core.output_parsers import JsonOutputParser


llm = ChatOllama(model="cow/gemma2_tools:2b")

_template_question_generation = """
You are task preprocessor agent. Your task is to create
a helful question from the given sentence. This Question is helful for generting
Question which can generate python code.
Make sure you dont generate code just create a question. 

Example.

USER REQUEST: "What is the system time?"
OUTPUT: Generate Python code to get the current system time using the time library.

Example 2:
USER REQUEST: "How can I calculate the square root of a number?"
OUTPUT: Generate Python code to calculate the square root of a number using the math library.

query : {query}
"""


_template_code_generation = """
For given Question create a python code.
In return just given python code nothing else.
Make sure code is wrapped in ```python ... ```` format.
Make neccesary imports whenever required
Dont write examples in the code just return code only.
question: {question}
"""

_template_code_review ="""
You are a code review agent. Your goal is to review Python code and determine whether it is correct, fully executable, and whether it solves the initial request.
Guidelines:
    - If the input contains anything other than Python code (e.g., comments, backticks, markdown syntax), return the comment 'incorrect' and a message stating the issue.
    - If the code is correct, return the comment 'correct' and message as why you evaluated that the code is correct.
    - If the code has issues (e.g., syntax errors, missing imports, inefficient logic), return the comment 'incorrect' with a message suggesting how to fix the code.
    - If the code does not appear to solve the initial request, return 'incorrect' with a message that the code doesn't solve the task.

In return give json containing inforamtion code is correct or not.
if not correct then pass message what should we improve in given code
json keys should be `is_correct` and `improvement` and main key should be `data`
for key `is_correct` always take value between [correct, incorrect]
dont give corrected code in the improvement key. improvement message should be the short and simple


extracted code : {extracted_code}

"""


_prompt_question = PromptTemplate.from_template(_template_question_generation)
_prompt_code_generation = PromptTemplate.from_template(_template_code_generation)
_prompt_review = PromptTemplate.from_template(_template_code_review)

question_llm = (_prompt_question | llm)
code_llm = (_prompt_code_generation | llm)
review_llm = (_prompt_review | llm | JsonOutputParser())



class AgentState(TypedDict):
    init_request :str
    code: str
    prepro_qn : str
    num_steps : int
    extracted_code : str
    is_correct: str
    code_improvement: str
    code_result : str



FINAL_CODE = ""


def question_agent(state):
    response = question_llm.invoke(state["init_request"])
    state["prepro_qn"] = response.content
    return state


def code_agent(state):
    response = code_llm.invoke(state["prepro_qn"])
    state["code"] = response.content
    return state

def _extract_code(text):
    # Regular expression to find code blocks enclosed with ```python ```
    pattern = r"```python(.*?)```"
    # Use re.DOTALL to match across multiple lines
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]

def extract_code_tool(state):
    """Use this tool to extract python code."""

    extracted_code =  _extract_code(state["code"])[0]
    state["extracted_code"] = extracted_code

    return state

def review_agent(state):
    
    data  =  review_llm.invoke(state["extracted_code"])
    print("################")
    print(data)
    print("################")
    state["is_correct"] = data["is_correct"]

    FINAL_CODE = state["extracted_code"]

    return state


def ROUTER_regenerate_code(state):
    if state["is_correct"]  == "correct":
        return "END"
    else:
        return "new"    


import os
def PYTHON_RUNNER(state):
    with open("mycode.py", "w") as file:
        file.write(state["extracted_code"])
        print("--- code saved ssfly ---")
    
    result = subprocess.run(["python", "mycode.py"], text=True, capture_output=True)
    state["code_result"] = result.stdout
    return state
    






def pretty_printer(state):
    print("--- print ---")
    print("REQUEST: ")
    print(colored(f"{state['init_request']}\n",color="magenta"))
    print("Generated Question: ")
    print(colored(f"{state['prepro_qn']}\n",color="red"))
    print("CODE: ")
    print(colored(f"{state['code']}\n ",color="yellow"))
    print("Extracted CODE: ")
    print(colored(f"{state['extracted_code']}\n ",color="yellow"))
    print("Correct or Incorrect")
    print(colored(f"{state['is_correct']}\n ",color="light_cyan"))
    print("Result : ")
    print(colored(f"{state['code_result']}\n ",color="green"))




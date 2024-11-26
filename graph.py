from langgraph.graph import StateGraph, START, END, add_messages
from typing_extensions import TypedDict, Annotated
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from agent import (code_agent,question_agent,pretty_printer,PYTHON_RUNNER,
                AgentState,extract_code_tool, review_agent, ROUTER_regenerate_code)


my_tools = [extract_code_tool]



workflow = StateGraph(AgentState)

### Node
workflow.add_node("question_agent",question_agent)
workflow.add_node("code_agent",code_agent)
workflow.add_node("exteact_tool",extract_code_tool)
workflow.add_node("review_agent", review_agent)
workflow.add_node("printing", pretty_printer)
workflow.add_node("runner", PYTHON_RUNNER)

### Edge
workflow.add_edge(START,"question_agent")
workflow.add_edge("question_agent","code_agent")
workflow.add_edge("code_agent","exteact_tool")
workflow.add_edge("exteact_tool","review_agent")
##
workflow.add_conditional_edges("review_agent", ROUTER_regenerate_code,{"END":END, "new": "code_agent" })
##
workflow.add_edge("review_agent","runner")
workflow.add_edge("runner","printing")

workflow.add_edge("printing",END)


memory = MemorySaver()
graph = workflow.compile(memory)

# graph.get_graph().draw_mermaid_png(output_file_path="graph-new.png")

config = dict(configurable=dict(thread_id=1))





def chat(q,history):
    config = dict(configurable=dict(thread_id=1))
    result = graph.invoke({"init_request":q},config=config)

    output = f"""
    Code: 
    {result['extracted_code']}
    {result['code_result']}    
     """

    return output

# while True:
#     q = input(" Question: ")
#     if q !="q":
#         result = graph.stream({"init_request":[q]},stream_mode="values",config=config)
#         for i in result:
#             print(i["init_request"])
#     else:
#         print("exiting")
#         break        

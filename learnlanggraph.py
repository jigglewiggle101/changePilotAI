from typing import Any
from typing_extensions import TypedDict

import ollama
from langgraph.graph import StateGraph, START, END

from app.tools.enterprise_data import (
    get_service_dependencies,
    get_transitive_dependencies,
    get_dependent_services,
    get_transitive_dependents
)

from app.tools.ticket_search import search_change_tickets

MODEL = "qwen2.5:14b"


class ChangeState(TypedDict):
    tool_name: str | None
    user_query: str
    tool_arguments: dict[str, Any] | None
    tool_result: Any
    model_message: str
    answer: str



DEPENDENCY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_service_dependencies",
        "description": "Find the direct dependencies of an enterprise service.",
        "parameters": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string"}
            },
            "required": ["service_id"]
        }
    }
}

TRANSITIVE_DEPENDENCY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_transitive_dependencies",
        "description": "Find all direct and indirect dependencies of a service recursively.",
        "parameters": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string"}
            },
            "required": ["service_id"]
        }
    }
}

DEPENDENT_SERVICES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_dependent_services",
        "description": "Find services that directly depend on the specified service.",
        "parameters": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string"}
            },
            "required": ["service_id"]
        }
    }
}

TRANSITIVE_DEPENDENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_transitive_dependents",
        "description": "Find all direct and indirect services that depend on the specified service.",
        "parameters": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string"}
            },
            "required": ["service_id"]
        }
    }
}

TICKET_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_change_tickets",
        "description": (
            "Search enterprise incident tickets by keyword. "
            "Use this when the user asks about incidents, tickets, "
            "outages, errors, timeouts, or historical service issues. "
            "Search using a relevant service ID, service name, "
            "or incident keyword."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": (
                        "A keyword, service ID, service name, "
                        "or incident term to search for."
                    )
                }
            },
            "required": ["keyword"]
        }
    }
}

def select_tool(state: ChangeState) -> dict:
    """Ask the local LLM whether to use the dependency lookup tool."""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                         "You are an enterprise change investigation assistant. "

                         "Choose the most appropriate tool based on the user's intent. "

                         "Use get_service_dependencies for direct dependencies only. "

                         "Use get_transitive_dependencies for all direct and indirect dependencies. "

                         "Use get_dependent_services to find services that directly depend on a service. "

                         "Use get_transitive_dependents to find all direct and indirect dependent services. "

                         "Use search_change_tickets for incidents, tickets, outages, "
                         "timeouts, or historical issues. "

                         "Always extract the actual service ID or exact service name "
                         "from the user's question. Never use placeholder values. "

                         "Do not invent enterprise data. "
                         "If no tool is relevant, answer the user without calling a tool."
)
            },
            {
                "role": "user",
                "content": (
                    state["user_query"]
                )
            }
        ],
        tools=[
       DEPENDENCY_TOOL,
       TICKET_SEARCH_TOOL,TRANSITIVE_DEPENDENCY_TOOL,
    DEPENDENT_SERVICES_TOOL,
    TRANSITIVE_DEPENDENTS_TOOL,
       ],
        options={
        "temperature": 0,
        "num_predict": 128
    }
    )

    message = response.message
    tool_name = None
    tool_arguments = None

    if message.tool_calls:
        for tool_call in message.tool_calls:
            if tool_call.function.name in {
             "get_service_dependencies",
             "search_change_tickets",
             "get_transitive_dependencies",
             "get_dependent_services",
             "get_transitive_dependents",
        }:
                tool_name = tool_call.function.name
                tool_arguments = dict(tool_call.function.arguments)
                break

    return {
        "tool_name": tool_name,
        "tool_arguments": tool_arguments,
        "model_message": message.content or ""
    }


def route_after_selection(state: ChangeState) -> str:
    """Choose the next node based on whether a tool was selected."""

    if state["tool_arguments"] is not None:
        return "execute_tool"

    return "explain_result"


def execute_tool(state: ChangeState) -> dict:
    """Execute the real Python function selected by the model."""

    tool_name = state["tool_name"]
    arguments = state["tool_arguments"] or {}

    # Map each allowed tool name to its actual Python function.
    available_tools = {
        "get_service_dependencies": get_service_dependencies,
        "get_transitive_dependencies": get_transitive_dependencies,
        "get_dependent_services": get_dependent_services,
        "get_transitive_dependents": get_transitive_dependents,
        "search_change_tickets": search_change_tickets
    }

    # Check that the selected tool is supported.
    if tool_name not in available_tools:
        result = {
            "error": f"Unsupported tool: {tool_name}"
        }
        return {"tool_result": result}

    # Execute the selected function with the model-provided arguments.
    tool_function = available_tools[tool_name]
    result = tool_function(**arguments)

    print("\nTool executed:", tool_name)
    print("Tool input:", arguments)
    print("Tool result:", result)

    return {"tool_result": result}


def explain_result(state: ChangeState) -> dict:
    """Interpret tool results dynamically and generate an evidence-based answer."""

    if state["tool_result"] is None:
        return {"answer": state["model_message"] or "I couldn't find relevant information."}

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an enterprise change investigation assistant. "

                    "Your responsibility is to interpret tool results and "
                    "answer the user's original question accurately. "

                    "Use the original question, selected tool name, and "
                    "tool result to understand the context. "

                    "Adapt your explanation to the type of information returned. "

                    "For dependency results, distinguish direct and indirect "
                    "dependencies. When the returned data contains enough "
                    "information, show the dependency paths as a readable tree. "

                    "For dependent-service results, identify which services "
                    "depend on the queried service. Distinguish direct and "
                    "indirect dependents where applicable. "

                    "For incident ticket results, summarise relevant incidents "
                    "using the available ticket details, such as title, status, "
                    "severity, affected service, and summary. "

                    "Use only information present in the tool result. "
                    "Never invent services, relationships, incidents, "
                    "risk assessments, or criticality values. "

                    "If the result indicates that a service was not found, "
                    "clearly state that it was not found in the dataset. "

                    "If no matching records are returned, explain that no "
                    "matching records were found in the available dataset. "

                    "Clearly communicate limitations and missing information. "
                    "Do not make assumptions beyond the supplied evidence. "
                    "Use a clear and structured response."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Original user question: {state['user_query']}\n"
                    f"Selected tool: {state['tool_name']}\n"
                    f"Tool arguments: {state['tool_arguments']}\n"
                    f"Tool result: {state['tool_result']}\n\n"
                    "Interpret these results and answer the original question."
                )
            }
        ],
        options={
            "temperature": 0,
            "num_predict": 512
        }
    )

    return {
        "answer": response.message.content or "No explanation returned."
    }

builder = StateGraph(ChangeState)

builder.add_node("select_tool", select_tool)
builder.add_node("execute_tool", execute_tool)
builder.add_node("explain_result", explain_result)

builder.add_edge(START, "select_tool")

builder.add_conditional_edges(
    "select_tool",
    route_after_selection,
    {
        "execute_tool": "execute_tool",
        "explain_result": "explain_result"
    }
)

builder.add_edge("execute_tool", "explain_result")
builder.add_edge("explain_result", END)

graph = builder.compile()


if __name__ == "__main__":

    print("\nChangePilot AI is ready!")
    print("Type 'exit' to quit.\n")

    while True:
        user_query = input("You: ").strip()

        if user_query.lower() in {"exit", "quit"}:
            print("ChangePilot AI session ended.")
            break

        if not user_query:
            continue

        initial_state: ChangeState = {
            "tool_name": None,
            "user_query": user_query,
            "tool_arguments": None,
            "tool_result": None,
            "model_message": "",
            "answer": ""
        }

        result = graph.invoke(initial_state)

        print("\nChangePilot AI:")
        print(result["answer"])
        print()
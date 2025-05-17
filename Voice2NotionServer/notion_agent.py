from typing import Any, TypedDict, Annotated, Sequence
from langchain.globals import set_debug, set_verbose
from langgraph.graph import Graph, StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from notion_client import AsyncClient
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import pytz

load_dotenv()

set_debug(True)
set_verbose(True)

# Define our state
class AgentState(MessagesState):
    pass

# Define our models
class NotionProperty(BaseModel):
    """Base model for Notion properties"""
    type: str = Field(..., description="The type of the Notion property (e.g., title, status, select)")
    value: dict = Field(..., description="The value of the property formatted according to Notion's API structure")

class CreateTaskInput(BaseModel):
    """Input schema for creating a new task"""
    properties: dict[str, NotionProperty] = Field(
        default_factory=lambda: {
            "Name": NotionProperty(
                type="title",
                value={"title": [{"text": {"content": "New Task"}}]}
            ),
            "Status": NotionProperty(
                type="status",
                value={"status": {"name": "Not started"}}
            ),
            "Priority": NotionProperty(
                type="select",
                value={"select": {"name": "Medium"}}
            )
        },
        description="Dictionary of property names to their values. Must include Name, Status, and Priority."
    )

class AddMovieInput(BaseModel):
    """Input schema for adding a movie to the watch list"""
    title: str = Field(..., description="Title of the movie")

# Define our tools
async def get_database_schema() -> dict:
    """Get the schema of the Notion database"""
    notion = AsyncClient(auth=os.getenv("NOTION_TOKEN"))
    database_id = os.getenv("NOTION_DATABASE_ID")
    response = await notion.databases.retrieve(database_id=database_id)
    return response

async def create_new_task(task_input: CreateTaskInput) -> str:
    """Create a new task in the Notion database"""
    notion = AsyncClient(auth=os.getenv("NOTION_TOKEN"))
    page_id = os.getenv("NOTION_PAGE_ID")
    
    # Convert the properties to Notion's format
    properties = {}
    for name, prop in task_input.properties.items():
        properties[name] = prop.value
    
    response = await notion.pages.create(
        parent={"database_id": page_id},
        properties=properties
    )
    print(f"Created task in Notion: {response}")
    return "Created task in Notion."

async def add_to_movie_list(movie_input: AddMovieInput) -> str:
    """Add a movie to the Notion movie list"""
    notion = AsyncClient(auth=os.getenv("NOTION_TOKEN"))
    movie_db_id = os.getenv("NOTION_MOVIE_DATABASE_ID")
    if not movie_db_id:
        raise ValueError("NOTION_MOVIE_DATABASE_ID is not set")
    response = await notion.pages.create(
        parent={"database_id": movie_db_id},
        properties={
            "Name": {"title": [{"text": {"content": movie_input.title}}]}
        }
    )
    print(f"Added movie to Notion: {response}")
    return "Added movie to Notion."

# Create tools
tools = [
    # StructuredTool.from_function(
    #     func=get_database_schema,
    #     name="get_database_schema",
    #     description="Get the schema of the Notion database"
    # ),
    StructuredTool.from_function(
        coroutine=create_new_task,
        name="create_new_task",
        description="Create a new task in the Notion database"
    ),
    StructuredTool.from_function(
        coroutine=add_to_movie_list,
        name="add_to_movie_list",
        description="Add a movie to the Notion movie list"
    )
]

# Create the prompt
prompt = ChatPromptTemplate.from_messages([
("system", """You are a helpful assistant that creates Notion database entries based on voice input.
    Your job is to extract task information from natural language input and create appropriate Notion tasks or add movies to a watch list.

    Available tools:
    - create_new_task: create a new task in the tasks database.
    - add_to_movie_list: add a movie title to the movie list database.
    
    You should follow these steps:
    1. Extract task properties from the natural language input:
       - Name: Use the main action/objective as the task name
       - Priority: Look for priority indicators (high, medium, low, etc.)
       - Due date: Look for date references
       - Tags: Infer appropriate tags from the context
       - Status: Always use "Not started" for new tasks
       - Size: Infer from complexity if mentioned
    
    2. Create the task using the CreateTaskInput model with the extracted properties
    
    The database is a task management system with the following properties:
    - Name (title): The task name
    - Status (status): Current status (Not started, In progress, Done, Blocked)
    - Priority (select): Task priority (Today, ASAP, High, Medium, Low, People)
    - Due date (date): When the task is due.
    - Tags (multi_select): Task categories
    - Size (number): Task size/complexity
    
    IMPORTANT: You must use the CreateTaskInput model when creating tasks. The model expects a dictionary of properties where each property is a NotionProperty object with:
    - type: The type of the property (e.g., "title", "status", "select")
    - value: The property value formatted according to Notion's API structure
    
    Example of correct property formatting:
    {{
        "properties": {{
            "Name": {{
                "type": "title",
                "value": {{"title": [{{"text": {{"content": "Task name"}}}}]}}
            }},
            "Status": {{
                "type": "status",
                "value": {{"status": {{"name": "Not started"}}}}
            }},
            "Priority": {{
                "type": "select",
                "value": {{"select": {{"name": "Medium"}}}}
            }}
        }}
    }}
    
    DO NOT ask for more information unless the input is completely unclear.
    Instead, try to extract as much as possible from the given input and use sensible defaults:
    - Status: Always "Not started" for new tasks, unless the user specifies otherwise.
    - Priority: Default to "ASAP" if not specified. The order of priority is Today, ASAP, High, Medium, Low, People (a special priority to track notes about specific people).
    - Due date (date): When the task is due. For your reference, the current time is {current_time} - use this as a reference point.
    - Tags: Leave empty if not clear from context
    - Size: Omit if not mentioned
    """),
    MessagesPlaceholder(variable_name="messages")
])

# Create the LLM
llm = ChatOpenAI(temperature=0, model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)

def notion_chat(state: AgentState) -> AgentState:
    """Notion reasoning to create a task"""
    messages = state["messages"]
    response = llm_with_tools.invoke(prompt.format_messages(
        current_time=datetime.now(tz=pytz.timezone('America/Puerto_Rico')).strftime("%Y-%m-%d %H:%M:%S"),
        messages=messages
    ))

    return {
        "messages": [response]
    }



# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
# workflow.add_node("get_schema", get_schema)
tool_node = ToolNode(tools=tools)
workflow.add_node("tools", tool_node)
workflow.add_node("notion_chat", notion_chat)
workflow.add_conditional_edges(
    "notion_chat",
    tools_condition
)
# Any time a tool is called, we return to the chatbot to decide the next step
workflow.add_edge("tools", "notion_chat")
workflow.set_entry_point("notion_chat")

# workflow.add_edge("get_schema", "create_task")
workflow.add_edge("notion_chat", END)

# Compile the graph
chain = workflow.compile()


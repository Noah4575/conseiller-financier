from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
from langgraph.graph.message import add_messages  # type: ignore

from typing_extensions import Annotated, TypedDict, List
from typing import Sequence


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str
    context: List[Document]
    user_profile: dict

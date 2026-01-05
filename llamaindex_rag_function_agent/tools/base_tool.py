from abc import ABC, abstractmethod
from typing import Any, Dict
from llama_index.core.tools import FunctionTool


class BaseTool(ABC):
    """Base class for all tools in the golf RAG system"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    async def _execute(self, **kwargs) -> Any:
        pass

    def to_llama_tool(self) -> FunctionTool:
        """
        Convert to LlamaIndex FunctionTool.
        """
        return FunctionTool.from_defaults(
            async_fn=self._execute,
            name=self.name,
            description=self.description,
        )

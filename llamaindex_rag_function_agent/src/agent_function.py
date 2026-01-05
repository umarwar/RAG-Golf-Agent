import asyncio
import warnings
from contextlib import suppress
from typing import List, Optional, AsyncGenerator
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.openai import OpenAI
from llama_index.core.workflow import Context
from llama_index.core.llms import ChatMessage
from google.genai import types as genai_types

from src.query_engines import QueryEngineManager
from tools.golf_courses import GolfCoursesTool
from tools.app_manual import AppManualTool
from tools.scorecards import ScorecardTool
from tools.tee_details import TeeDetailsTool
from config.settings import GolfAgentConfig

# Suppress noisy Gemini → Pydantic serializer warnings
warnings.filterwarnings(
    "ignore", message="Pydantic serializer warnings", category=UserWarning
)


class GolfRAGAgentFunction:
    """Production-grade RAG Agent using FunctionAgent for better reliability"""

    SYSTEM_PROMPT = """You are an expert AI Golf assistant for the GolfGuiders application, designed to help users with all aspects of golf (courses, scorecards, tee details, etc.) and application usage.

## PRIMARY RESPONSIBILITIES:
1. **Golf Course Information**: Provide clear, detailed information about golf courses (address, holes, classification, types) and recommend courses based on user preferences and location.
2. **Application Support**: Help users understand and use GolfGuiders application features.
3. **Scorecard & Tee Details Information**: Provide detailed information about scorecards and tee details for a given course, with readable summaries.
4. **General Golf Knowledge**: Answer general golf-related questions when appropriate.

## TOOL SELECTION GUIDELINES:
- Use `search_golf_courses` for: golf course information, locations, facilities, types, holes, and recommendations. When the user needs scorecards or tee info, first find the relevant course so you can internally use its `id_course` (do not show course IDs).
- Use `search_app_manual` for: GolfGuiders application questions, troubleshooting, feature explanations, and usage.
- Use `search_scorecards` for: scorecard hole information, par totals, and rating data for a given course.
- Use `search_tee_details` for: tee colors, yardages, and ratings for a given course.

## IMPORTANT GUIDELINES:
- First decide if the user's request truly needs external data. Quick greetings, confirmations, or very simple questions should be answered directly without any tool call.
- You are a golf expert, so you should answer golf related questions. For clearly unrelated topics, politely decline and invite the user to ask a golf-related question instead.
- If multiple tools provide relevant information, synthesize the best answer into a well-structured response.
- Provide a clear and detailed answer so the user feels their question is fully answered. Ask follow-up questions if needed.
- Always be friendly, professional, and golf-enthusiastic.
- If you need clarification to give an accurate answer, ask follow-up questions."""

    def __init__(self, config: GolfAgentConfig):
        self.config = config

        # Initialize query engines
        print("✓ Query engines initialized")
        self.qe_manager = QueryEngineManager(self.config)

        # Initialize tools
        self.tools = self._initialize_tools()

        # Create agent
        self.agent = self._create_agent()

        print("✓ Agent initialized successfully\n")

    def _initialize_tools(self) -> List:
        """Initialize all available tools"""
        return [
            GolfCoursesTool(self.qe_manager).to_llama_tool(),
            AppManualTool(self.qe_manager).to_llama_tool(),
            ScorecardTool().to_llama_tool(),
            TeeDetailsTool().to_llama_tool(),
        ]

    def _create_agent(self) -> FunctionAgent:
        """Create the FunctionAgent"""
        # generation_config = genai_types.GenerateContentConfig(
        #     thinking_config=genai_types.ThinkingConfig(include_thoughts=False)
        # )

        # llm = GoogleGenAI(
        #     model=self.config.LLM_MODEL,
        #     temperature=self.config.LLM_TEMPERATURE,
        #     api_key=self.config.GOOGLE_API_KEY,
        #     generation_config=generation_config,
        # )

        llm = OpenAI(
            model=self.config.LLM_MODEL,
            temperature=self.config.LLM_TEMPERATURE,
            api_key=self.config.OPENAI_API_KEY,
        )

        return FunctionAgent(
            tools=self.tools,
            llm=llm,
            system_prompt=self.SYSTEM_PROMPT,
            streaming=True,
        )

    async def chat_streaming(
        self,
        message: str,
        context: Optional[Context] = None,
        chat_history: Optional[List[ChatMessage]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Chat with the agent with streaming response.

        Args:
            message: User's message
            context: Optional workflow context
            chat_history: List of ChatMessage objects from persistent storage (required)
        """
        if chat_history is None:
            chat_history = []

        try:
            # Create or use existing context
            if context is None:
                context = Context(self.agent)

            print(f"chat_history: {chat_history}")

            handler = self.agent.run(message, ctx=context, chat_history=chat_history)
            stream = handler.stream_events()

            try:
                async for event in stream:
                    if hasattr(event, "delta") and event.delta:
                        yield event.delta
            finally:
                with suppress(Exception):
                    await stream.aclose()
                with suppress(asyncio.CancelledError):
                    await handler

        except Exception as e:
            print(f"Error in streaming chat: {e}")
            yield f"I apologize, but I encountered an error: {str(e)}"

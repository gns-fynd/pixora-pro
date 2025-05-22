"""
Base agent class for Pixora AI Video Creation Platform
"""
import os
import logging
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Callable, Union, Awaitable

# Configure logging
logger = logging.getLogger(__name__)

# Import OpenAI
try:
    import openai
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("openai not installed. OpenAI-based agents will not work.")
    OPENAI_AVAILABLE = False
    openai = None
    OpenAI = None
    AsyncOpenAI = None

# Import telemetry
from ..utils.telemetry import traced, log_event

class BaseAgent:
    """
    Base class for all agents in the system.
    """
    
    def __init__(self, name: str, instructions: str, tools: Optional[List[Callable]] = None):
        """
        Initialize the base agent.
        
        Args:
            name: Name of the agent
            instructions: Instructions for the agent
            tools: Optional list of tools available to the agent
        """
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        
        # Initialize OpenAI client if available
        self.openai_client = None
        self.async_openai_client = None
        
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.async_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info(f"OpenAI client initialized for agent: {name}")
            except Exception as e:
                logger.error(f"Error initializing OpenAI client for agent {name}: {str(e)}")
        
        logger.info(f"Agent {name} initialized with {len(self.tools)} tools")
    
    @traced("run")
    async def run(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the agent with the given input.
        
        Args:
            input_text: Input text for the agent
            context: Optional context for the agent
            
        Returns:
            Dict[str, Any]: Response from the agent
        """
        # Create a trace ID for tracking
        trace_id = str(uuid.uuid4())
        
        # Log the agent run
        log_event(
            event_type="agent_run_started",
            message=f"Agent {self.name} run started",
            data={
                "agent": self.name,
                "input_length": len(input_text),
                "trace_id": trace_id
            }
        )
        
        # Initialize context if not provided
        if context is None:
            context = {}
        
        try:
            # Check if OpenAI is available
            if not OPENAI_AVAILABLE or not self.async_openai_client:
                # Fall back to direct API calls
                result = await self._run_with_direct_api(input_text, context)
            else:
                # Use OpenAI for agent execution
                result = await self._run_with_openai(input_text, context)
            
            # Log the agent run completion
            log_event(
                event_type="agent_run_completed",
                message=f"Agent {self.name} run completed",
                data={
                    "agent": self.name,
                    "trace_id": trace_id,
                    "status": "success"
                }
            )
            
            return result
        except Exception as e:
            # Log the agent run failure
            log_event(
                event_type="agent_run_failed",
                message=f"Agent {self.name} run failed: {str(e)}",
                data={
                    "agent": self.name,
                    "trace_id": trace_id,
                    "error": str(e),
                    "error_type": e.__class__.__name__
                }
            )
            
            # Re-raise the exception
            raise
    
    async def _run_with_openai(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent with OpenAI.
        
        Args:
            input_text: Input text for the agent
            context: Context for the agent
            
        Returns:
            Dict[str, Any]: Response from the agent
        """
        # This is a placeholder implementation
        # Subclasses should override this method with their own implementation
        return {
            "status": "error",
            "error": "Method not implemented"
        }
    
    async def _run_with_direct_api(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent with direct API calls.
        
        Args:
            input_text: Input text for the agent
            context: Context for the agent
            
        Returns:
            Dict[str, Any]: Response from the agent
        """
        # This is a placeholder implementation
        # Subclasses should override this method with their own implementation
        return {
            "status": "error",
            "error": "Method not implemented"
        }
    
    async def _call_tool(self, tool: Callable, **kwargs: Any) -> Any:
        """
        Call a tool with the given arguments.
        
        Args:
            tool: Tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Any: Result of the tool call
        """
        # Check if the tool is async
        if asyncio.iscoroutinefunction(tool):
            # Call the tool asynchronously
            return await tool(**kwargs)
        else:
            # Call the tool synchronously
            return tool(**kwargs)

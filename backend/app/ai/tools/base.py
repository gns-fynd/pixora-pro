"""
Base tool interface for Pixora AI Agent.

This module defines the base Tool class and ToolRegistry for managing tools.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class Tool(ABC):
    """
    Base class for all tools used by the Pixora AI Agent.
    
    Tools extend the agent's capabilities by providing specific functionality
    like scene breakdown, image generation, etc.
    """
    
    def __init__(self, name: str, description: str, parameters_schema: Dict[str, Any]):
        """
        Initialize a tool.
        
        Args:
            name: The name of the tool
            description: A description of what the tool does
            parameters_schema: JSON schema defining the tool's parameters
        """
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with the given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            A string containing the tool's output, typically JSON
        """
        pass
        
    def get_definition(self) -> Dict[str, Any]:
        """
        Get the tool definition for the OpenAI API.
        
        Returns:
            A dictionary containing the tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }


class ToolRegistry:
    """
    Registry for managing available tools.
    
    The ToolRegistry keeps track of all tools available to the agent
    and provides methods for registering and retrieving tools.
    """
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self.tools: Dict[str, Tool] = {}
        
    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool with the registry.
        
        Args:
            tool: The tool to register
        """
        self.tools[tool.name] = tool
        
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The tool if found, None otherwise
        """
        return self.tools.get(name)
        
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get the tool definitions for the OpenAI API.
        
        Returns:
            A list of tool definitions
        """
        return [tool.get_definition() for tool in self.tools.values()]
        
    def list_tools(self) -> List[str]:
        """
        List all registered tool names.
        
        Returns:
            A list of tool names
        """
        return list(self.tools.keys())

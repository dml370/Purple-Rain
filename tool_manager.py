
# FILE: tool_manager.py
# Final, Unabridged Version: June 29, 2025

import logging
import json
from functools import wraps

# The manager will import all available tool classes from the /tools/ directory
from tools.web_search_tool import WebSearchTool
from tools.computer_controller_tool import ComputerController

logger = logging.getLogger(__name__)

class ToolManager:
    """
    Discovers, registers, and executes all available tools for the AI agent.
    This acts as a secure and centralized dispatcher for all agent actions.
    """
    def __init__(self):
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        """Initializes and registers all available tool classes."""
        # Each tool class is instantiated and stored in a dictionary.
        # The key (e.g., 'web_browser') must match the name in the tool's schema.
        try:
            web_browser_tool = WebSearchTool()
            computer_controller_tool = ComputerController()
            
            self.tools[web_browser_tool.get_schema()['name']] = web_browser_tool
            self.tools[computer_controller_tool.get_schema()['name']] = computer_controller_tool
            
            # To add new tools, simply import their class and register them here.
            # self.tools['new_tool'] = NewToolClass()
            
            logger.info(f"Tool Manager initialized. Registered tools: {list(self.tools.keys())}")
        except Exception as e:
            logger.exception("Failed to register one or more tools.")

    async def execute_tool(self, tool_name: str, arguments: dict):
        """
        Executes a specific action on a named tool based on the arguments provided by the AI.
        """
        if tool_name not in self.tools:
            logger.error(f"Attempted to execute non-existent tool: {tool_name}")
            return {"error": f"Tool '{tool_name}' not found."}

        tool_instance = self.tools[tool_name]
        
        # The AI should specify which function of the tool to call via 'action_to_perform'
        action_name = arguments.pop('action_to_perform', None)
        if not action_name or not hasattr(tool_instance, action_name):
            logger.error(f"Tool '{tool_name}' was called without a valid 'action_to_perform' in its arguments.")
            return {"error": f"A valid 'action_to_perform' must be specified for tool '{tool_name}'."}

        method_to_call = getattr(tool_instance, action_name)
        
        try:
            logger.info(f"Executing action '{action_name}' on tool '{tool_name}' with args: {arguments}")
            # The remaining arguments are passed as keyword arguments to the action method
            return await method_to_call(**arguments)
        except Exception as e:
            logger.exception(f"Error executing {tool_name}.{action_name}: {e}")
            return {"error": f"An unexpected error occurred during tool execution: {str(e)}"}

    def get_tool_schemas_for_provider(self, provider_name: str = 'openai'):
        """
        Generates all available tool schemas in the format required by the specified AI provider.
        """
        all_schemas = []
        for tool_instance in self.tools.values():
            if hasattr(tool_instance, 'get_schema'):
                # The get_schema method on the tool itself returns its definition
                schema = tool_instance.get_schema()
                if schema:
                    all_schemas.append(schema)
        
        # This logic formats the schemas for different AI providers
        if provider_name == 'openai':
            return [{"type": "function", "function": schema} for schema in all_schemas]
        elif provider_name == 'anthropic':
            # Anthropic's format is slightly different, often not needing the outer dictionary
            return all_schemas
        
        return all_schemas # Default to a generic list

# Create a singleton instance to be used across the entire application.
tool_manager = ToolManager()

# FILE: tools/computer_controller_tool.py
# Final, Unabridged Version: June 29, 2025

import pyautogui
import asyncio
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ComputerController:
    """Provides full control over the host system's mouse and keyboard."""

    def __init__(self):
        pyautogui.FAILSAFE = False
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Computer Controller initialized. Screen size: {self.screen_width}x{self.screen_height}")

    async def _run_sync(self, func, *args, **kwargs):
        """Runs a synchronous pyautogui function in a thread to avoid blocking."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def move_to(self, x: int, y: int, duration: float = 0.5):
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))
        await self._run_sync(pyautogui.moveTo, x, y, duration=duration)
        return {"status": "success", "action": "move_to", "x": x, "y": y}

    async def click(self, button: str = 'left'):
        await self._run_sync(pyautogui.click, button=button)
        return {"status": "success", "action": "click", "button": button}

    async def type_text(self, text: str, interval: float = 0.01):
        await self._run_sync(pyautogui.write, text, interval=interval)
        return {"status": "success", "action": "type_text", "length": len(text)}

    async def press_keys(self, keys: List[str]):
        await self._run_sync(pyautogui.hotkey, *keys)
        return {"status": "success", "action": "press_keys", "keys": keys}

    def get_schema(self) -> dict:
        """Defines the tool's structure for the AI."""
        return {
            "name": "computer_controller",
            "description": "Directly controls the computer's keyboard and mouse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_to_perform": {"type": "string", "enum": ["move_to", "click", "type_text", "press_keys"]},
                    "x": {"type": "integer", "description": "X-coordinate for mouse movements."},
                    "y": {"type": "integer", "description": "Y-coordinate for mouse movements."},
                    "duration": {"type": "number", "description": "Time in seconds for the mouse movement."},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button to click."},
                    "text": {"type": "string", "description": "The text to type."},
                    "keys": {"type": "array", "items": {"type": "string"}, "description": "A list of keyboard keys to press simultaneously, e.g., ['ctrl', 'c']."}
                },
                "required": ["action_to_perform"]
            }
        }

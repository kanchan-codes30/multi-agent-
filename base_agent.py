"""
Base Agent class - all specialized agents inherit from this.
This gives every agent a common interface: run(), log(), and a name,
which is what makes the "multi-agent" orchestration in orchestrator.py possible.
"""
from abc import ABC, abstractmethod
import time


class BaseAgent(ABC):
    def __init__(self, name):
        self.name = name
        self.logs = []

    def log(self, message):
        entry = f"[{self.name}] {message}"
        self.logs.append(entry)
        print(entry)

    @abstractmethod
    def run(self, *args, **kwargs):
        """Every agent must implement its own run() method."""
        pass

    def timed_run(self, *args, **kwargs):
        """Wraps run() with timing, used by the orchestrator to show progress."""
        start = time.time()
        result = self.run(*args, **kwargs)
        duration = round(time.time() - start, 2)
        self.log(f"Completed in {duration}s")
        return result

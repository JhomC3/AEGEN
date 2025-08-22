# Specialist Architecture Template

## Directory Structure
```
src/agents/specialists/[specialist_name]/
├── __init__.py          # Module exports
├── agent.py            # Main SpecialistInterface implementation
├── graph_builder.py    # LangGraph construction (Factory pattern)
├── prompt_manager.py   # Prompt loading/management (if needed)
├── state_utils.py      # Pure functions for state manipulation
└── tool.py             # Tool definition for registry
```

## Code Templates

### 1. agent.py - Main Specialist Class
```python
# src/agents/specialists/[name]/agent.py
import logging
from typing import Any

from langchain_core.tools import BaseTool
from src.core.interfaces.specialist import SpecialistInterface
from src.core.registry import specialist_registry
from src.core.schemas import GraphStateV2

from .graph_builder import [Name]GraphBuilder
from .tool import [name]_tool
# Import other dependencies as needed

logger = logging.getLogger(__name__)

class [Name]Agent(SpecialistInterface):
    """
    [Brief description of specialist responsibility]

    Single Responsibility: [One sentence describing what this does]

    Dependencies:
    - [Name]GraphBuilder: Graph construction
    - [name]_tool: Tool exposure to registry
    """

    def __init__(self):
        self._name = "[name]_agent"
        self._tool: BaseTool = [name]_tool
        self._graph = [Name]GraphBuilder(self._main_node).build()

    @property
    def name(self) -> str:
        return self._name

    @property
    def graph(self) -> Any:
        return self._graph

    @property
    def tool(self) -> BaseTool:
        return self._tool

    def get_capabilities(self) -> list[str]:
        return ["capability1", "capability2"]

    async def _main_node(self, state: GraphStateV2) -> dict[str, Any]:
        """
        Core business logic - SINGLE RESPONSIBILITY only.
        Delegate everything else to utilities.
        """
        try:
            # Business logic here
            pass
        except Exception as e:
            logger.error(f"Error in [Name]Agent: {e}", exc_info=True)
            return {"error_message": str(e)}

# Register
specialist_registry.register([Name]Agent())
```

### 2. graph_builder.py - Graph Construction
```python
# src/agents/specialists/[name]/graph_builder.py
from typing import Any, Callable
from langgraph.graph import END, StateGraph
from src.core.schemas import GraphStateV2

class [Name]GraphBuilder:
    """
    Single Responsibility: Build LangGraph StateGraph for [Name]Agent.
    """

    def __init__(self, main_node_func: Callable):
        if not callable(main_node_func):
            raise TypeError("main_node_func must be callable")
        self._main_node = main_node_func

    def build(self) -> Any:
        """Build and compile StateGraph."""
        graph_builder = StateGraph(GraphStateV2)
        graph_builder.add_node("main", self._main_node)
        graph_builder.set_entry_point("main")
        graph_builder.add_edge("main", END)
        return graph_builder.compile()
```

### 3. state_utils.py - Pure Functions
```python
# src/agents/specialists/[name]/state_utils.py
"""Pure functions for [Name]Agent state manipulation."""
from src.core.schemas import GraphStateV2

def extract_[something]_from_state(state: GraphStateV2) -> str:
    """Pure function - no side effects."""
    # Extraction logic
    pass

def build_[something](data: Any) -> str:
    """Pure function - transformation only."""
    # Transformation logic
    pass
```

### 4. tool.py - Tool Definition
```python
# src/agents/specialists/[name]/tool.py
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def [name]_tool(input_param: str) -> str:
    """
    Tool description for [Name]Agent.
    """
    logger.info(f"[Name]Tool: Processing {input_param}")
    return f"[Name] processing: {input_param}"
```

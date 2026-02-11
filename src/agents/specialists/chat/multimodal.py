import base64
from typing import Any, cast

import aiofiles
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from src.core.engine import llm


async def process_image_input(
    image_path: str,
    prompt_input: dict[str, Any],
    prompt_template: ChatPromptTemplate,
    config: RunnableConfig,
) -> str:
    """Procesa entrada multimodal (texto + imagen)."""
    async with aiofiles.open(image_path, "rb") as f:
        image_data = base64.b64encode(await f.read()).decode("utf-8")

    formatted_prompt = await prompt_template.aformat(**prompt_input)
    content_list = [
        {"type": "text", "text": formatted_prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
        },
    ]
    response = await llm.ainvoke(
        [HumanMessage(content=cast(Any, content_list))],
        config=cast(RunnableConfig, config),
    )
    return str(response.content).strip()

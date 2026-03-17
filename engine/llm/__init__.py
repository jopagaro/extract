"""
LLM module.

Assembles prompts, routes requests to OpenAI or Anthropic,
and returns structured responses. All callers go through the router —
they never call provider clients directly.

Usage:
    from engine.llm.providers.router import call_llm
    from engine.core.enums import LLMRole, LLMTask

    response = await call_llm(
        role=LLMRole.ECONOMICS_ANALYST,
        task=LLMTask.EXTRACTION,
        task_name="extract_economic_assumptions",
        data="<document text here>",
    )
    print(response.content)
"""

"""Agents"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from langchain_classic.agents import AgentExecutor, create_react_agent, create_tool_calling_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
from par_ai_core.llm_config import llm_run_manager
from par_ai_core.llm_image_utils import image_to_chat_message
from par_ai_core.output_utils import DisplayOutputFormat, get_output_format_prompt
from par_ai_core.utils import (
    code_frontend_file_globs,
    code_java_file_globs,
    code_js_file_globs,
    code_python_file_globs,
    code_rust_file_globs,
    gather_files_for_context,
)
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

# Memory utils import moved inside functions to prevent Redis connection when disabled
from par_gpt.utils import get_console

# Matches OpenAI reasoning-family model names: the o-series (o1, o3, o4, ...) and
# gpt-5.x variants, including -mini/-preview/-nano suffixes. These models need special
# prompt handling (e.g. suppressing the system prompt).
_REASONING_MODEL_RE = re.compile(r"^(o\d|gpt-5)", re.IGNORECASE)


def is_reasoning_model(chat_model: BaseChatModel) -> bool:
    """Return True if ``chat_model`` is an OpenAI reasoning-family model.

    Covers the o-series (o1, o3, o4 and successors) and gpt-5.x variants. These models
    require special prompt handling such as suppressing the system prompt.
    """
    name = getattr(chat_model, "name", None) or ""
    return bool(_REASONING_MODEL_RE.match(name))


def do_single_llm_call(
    *,
    chat_model: BaseChatModel,
    user_input: str,
    image: str | None = None,
    system_prompt: str | None = None,
    no_system_prompt: bool = False,
    env_info: str | None = None,
    display_format: DisplayOutputFormat = DisplayOutputFormat.NONE,
    chat_history: list[tuple[str, str | list[dict[str, Any]]]] | None = None,
    debug: bool,
    console: Console | None = None,
) -> tuple[str, str, BaseMessage]:
    """Perform a single LLM invocation and return its content, thinking, and message.

    Builds the chat history (memory prompt, system prompt, environment info, output-format
    directive, optional image, and prior turns), invokes the model, and normalizes the response
    into a plain content string plus any captured reasoning ("thinking") text.

    Args:
        chat_model: The chat model to invoke.
        user_input: The user's prompt text.
        image: Optional image to attach to the user turn (model-dependent).
        system_prompt: Override for the system prompt. Falls back to a default that is augmented
            with persisted memories when omitted.
        no_system_prompt: When True, suppress the system prompt entirely (used for reasoning
            models that require it).
        env_info: Environment/system context appended to the system prompt.
        display_format: Output-format directive folded into the system prompt.
        chat_history: Prior conversation turns as ``(role, content)`` pairs. A leading ``system``
            turn is replaced rather than duplicated.
        debug: Print the resolved prompt panel before invoking.
        console: Console to print debug output to. Defaults to the shared console.

    Returns:
        A ``(content, thinking, result)`` tuple where ``content`` is the normalized response
        text, ``thinking`` is any captured reasoning text, and ``result`` is the underlying
        ``BaseMessage`` (with ``content`` replaced by the normalized string).

    Raises:
        PydanticValidationError: If the provider rejects the constructed message history.
        Exception: Propagates any error raised by ``chat_model.invoke``.
    """
    console = get_console(console)

    if not env_info:
        env_info = ""

    if chat_history is None:
        chat_history = []

    default_system_prompt = """<purpose>You are a helpful assistant. Try to be concise and brief unless the user requests otherwise. If an output_instructions section is provided, follow its instructions for output.</purpose>"""
    # Import memory utils here to avoid Redis connection when Redis is disabled
    from par_gpt.memory_utils import get_memory_prompt

    memories = get_memory_prompt()
    if memories:
        default_system_prompt += memories
    if not no_system_prompt:
        output_format = get_output_format_prompt(display_format)
        if chat_history and chat_history[0][0] == "system":
            chat_history.pop(0)
        chat_history.insert(
            0,
            (
                "system",
                (system_prompt or default_system_prompt).strip() + "\n" + env_info + "\n" + output_format,
            ),
        )

        # Groq does not support images if a system prompt is specified
        if isinstance(chat_model, ChatGroq) and image:
            chat_history.pop(0)

    chat_history_debug = copy.deepcopy(chat_history)
    if image:
        chat_history.append(("user", [{"type": "text", "text": user_input}, image_to_chat_message(image)]))
        chat_history_debug.append(("user", [{"type": "text", "text": user_input}, ({"IMAGE": "DATA"})]))
    else:
        chat_history.append(("user", user_input))
        chat_history_debug.append(("user", user_input))

    if debug:
        console.print(Panel.fit(Pretty(chat_history_debug), title="GPT Prompt"))

    # Time the LLM call
    from par_utils import timer

    with timer("llm_invoke", {"model": chat_model.name}):
        result = chat_model.invoke(chat_history, config=llm_run_manager.get_runnable_config(chat_model.name))  # type: ignore
    # console.print(result)
    content = ""
    thinking = ""
    if isinstance(result.content, str):
        content = result.content.replace("```markdown", "").replace("```", "").strip()
    elif isinstance(result.content, list):
        for item in result.content:
            if isinstance(item, str):
                content += item.replace("```markdown", "").replace("```", "").strip() + "\n"
            elif isinstance(item, dict):
                if "text" in item:
                    content += item["text"].replace("```markdown", "").replace("```", "").strip() + "\n"
                if "thinking" in item:
                    thinking += item["thinking"] + "\n"

    result.content = content.strip()
    return content, thinking, result


# not currently used
def do_react_agent(
    chat_model: BaseChatModel,
    ai_tools: list[BaseTool],
    env_info: str,
    question: str,
    system_prompt: str | None,
    max_iterations: int = 5,
    debug: bool = False,
    verbose: bool = True,
    console: Console | None = None,
):
    """Run a ReAct-style agent that reasons and acts over the provided tools.

    Builds a ReAct prompt (tools, scratchpad, question), executes it with an
    ``AgentExecutor``, and returns the final answer.

    Args:
        chat_model: The chat model driving the agent.
        ai_tools: Tools the agent may call.
        env_info: Environment/system context folded into the prompt.
        question: The user's question to answer.
        system_prompt: Optional override for the full ReAct prompt template.
        max_iterations: Maximum agent iterations before forcing a final answer.
        debug: Print the resolved prompt panel before execution.
        verbose: Forwarded to ``AgentExecutor`` for verbose logging.
        console: Console for debug output.

    Returns:
        A ``(content, result)`` tuple where ``content`` is the normalized final
        answer and ``result`` is the executor's result mapping.
    """
    console = get_console(console)

    default_system_prompt = (
        """
You are a helpful assistant. Try to be concise and brief unless the user requests otherwise.
You have the following tools available:

{tools}

"""
        + env_info
        + """
Use tools and extra_context section to help answer the question.
When doing a web search determine which of the results is best and only download content from that result.
YOU MUST USE THE FOLLOWING FORMAT:
```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```
When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!

# Question
{question}

# Agent Scratchpad
{agent_scratchpad}
        """
    )

    prompt_template = PromptTemplate.from_template(system_prompt or default_system_prompt)
    agent = create_react_agent(chat_model, ai_tools, prompt_template)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=ai_tools,
        handle_parsing_errors=True,
        verbose=verbose,
        max_iterations=max_iterations,
    )
    if debug:
        console.print(Panel.fit(default_system_prompt, title="GPT Prompt"))

    # Time the agent executor call
    from par_utils import timer

    with timer("agent_executor_invoke", {"model": chat_model.name}):
        result = agent_executor.invoke(
            {"question": question}, config=llm_run_manager.get_runnable_config(chat_model.name)
        )
    content = str(result["output"]).replace("```markdown", "").replace("```", "").strip()
    result["output"] = content
    return content, result


def do_tool_agent(
    *,
    chat_model: BaseChatModel,
    ai_tools: list[BaseTool],
    modules: list[str],
    env_info: str,
    user_input: str,
    system_prompt: str | None,
    image: str | None = None,
    max_iterations: int = 5,
    chat_history: list[tuple[str, str | list[dict[str, Any]]]] | None = None,
    debug: bool = True,
    verbose: bool = False,
    console: Console | None = None,
):
    """Run a tool-calling agent that selects and invokes tools to answer the user.

    Constructs a tool-calling agent from the model and tools, executes it with an
    ``AgentExecutor``, and returns the final answer.

    Args:
        chat_model: The chat model driving the agent.
        ai_tools: Tools the agent may call.
        env_info: Environment/system context folded into the prompt.
        user_input: The user's request.
        system_prompt: Optional system prompt override.
        image: Optional image attached to the user turn.
        max_iterations: Maximum agent iterations.
        chat_history: Prior conversation turns.
        debug: Print the resolved prompt panel before execution.
        verbose: Forwarded to ``AgentExecutor`` for verbose logging.
        console: Console for debug output.

    Returns:
        A ``(content, result)`` tuple where ``content`` is the normalized final
        answer and ``result`` is the executor's result mapping.
    """

    if image:
        raise ValueError("Image not supported for tool agent")

    console = get_console(console)

    if chat_history is None:
        chat_history = []

    # Import memory utils here to avoid Redis connection when Redis is disabled
    from par_gpt.memory_utils import get_memory_prompt

    memories = get_memory_prompt()

    has_repl = False
    for tool in ai_tools:
        if "repl" in tool.name.lower():
            has_repl = True
            break

    if has_repl and modules:
        module_text = (
            "<available_modules>\n"
            + ("\n".join([f"    <module>{module}</module>" for module in modules]) + "\n")
            + "</available_modules>\n"
        )
    else:
        module_text = ""

    default_system_prompt = """
<role>You are a helpful assistant.</role>
<instructions>
    <instruction>Think through all the steps needed to answer the question and make a plan before using tools.</instruction>
    <instruction>Answer the users question, try to be concise and brief unless the user requests otherwise.</instruction>
    <instruction>If you need more information or clarification from the user use the `user_prompt` tool.</<instruction>
    <instruction>If an output_instructions section is present follow its instructions.</instruction>
    <instruction>If a tool returns an error message asking you to stop, do not make any additional requests and use the error message as the final answer.</instruction>
    <instruction>Use tools and the extra_context section to help answer the question.</instruction>
    <instruction>If a tool states its output should be returned directly to user ensure you return it directly to the use without modifications.</instruction>
    <instruction>When doing a web search determine which of the results is best and only download content from that result.</instruction>
    <instruction>When creating code you MUST follow the rules in the code_rules section.</instruction>
"""
    if memories:
        default_system_prompt += memories

    if has_repl:
        default_system_prompt += """
    <instruction>When using a REPL tool you MUST follow the rules in the repl_rules section.</instruction>
"""
    default_system_prompt += """
</instructions>
"""
    if has_repl:
        default_system_prompt += """
<repl_rules>
    <rule>DO NOT install any packages.</rule>
    <rule>NEVER execute code that could destroy data or otherwise harm the system or its data and files.</rule>
    <rule>The available_modules are already available and do not need to be imported.</rule>
    <rule>Do not include imports in your code reference the module name instead.</rule>
    <rule>Use console.print() to output text to the user. This console.print supports markup formatting using the rich library.</rule>
    <rule>If an "AbortedByUserError" is raised by a tool, return its message to the user as the final answer.</rule>
</repl_rules>
"""

    default_system_prompt += """
<code_rules>
    <rule>Assume python version is 3.12</rule>
    <rule>Ensure any web requests have a 10 second timeout.</rule>
    <rule>Ensure that encoding is set to "utf-8" for all file operations.</rule>
</code_rules>

{module_text}

{env_info}

<chat_history>
{chat_history}
</chat_history>

<user_input>
{user_input}
</user_input>

<agent_scratchpad>
{agent_scratchpad}
</agent_scratchpad>
"""
    prompt = system_prompt or default_system_prompt
    if "{agent_scratchpad}" not in prompt:
        prompt += "\n<agent_scratchpad>\n{agent_scratchpad}\n</agent_scratchpad>\n"
    prompt_template = ChatPromptTemplate.from_template(prompt)

    chat_history.append(("user", user_input))

    agent = create_tool_calling_agent(chat_model, ai_tools, prompt_template)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=ai_tools,
        handle_parsing_errors=True,
        verbose=verbose,
        max_iterations=max_iterations,
        stream_runnable=False,  # type: ignore
        # early_stopping_method="generate",
    )
    args = {"user_input": user_input, "module_text": module_text, "env_info": env_info, "chat_history": chat_history}
    if debug:
        console.print(Panel.fit(prompt_template.format(**args, agent_scratchpad=""), title="GPT Prompt"))

    # Time the tool agent executor call
    from par_utils import timer

    with timer("tool_agent_executor_invoke", {"model": chat_model.name}):
        result = agent_executor.invoke(args, config=llm_run_manager.get_runnable_config(chat_model.name))
    if isinstance(result["output"], str):
        content = result["output"]
    else:
        content = result["output"][0]["text"]
    content = content.replace("```markdown", "").replace("```", "").strip()
    chat_history.append(("assistant", content))
    return content, result


def do_code_review_agent(
    *,
    chat_model: BaseChatModel,
    env_info: str,
    user_input: str,
    system_prompt: str | None,
    display_format: DisplayOutputFormat,
    debug: bool = True,
    console: Console | None = None,
) -> tuple[str, str, BaseMessage]:
    """Run a code-review pass over the project and return bug-analysis findings.

    Gathers source files from the project, renders the bug-analysis prompt
    (``prompts/prompt_bug_analysis.xml``) with that code context, and delegates to
    ``do_single_llm_call``.

    Args:
        chat_model: The chat model performing the review.
        env_info: Environment/system context folded into the prompt.
        user_input: The user's review instructions.
        system_prompt: Optional override for the bug-analysis prompt template.
        display_format: Output-format directive.
        debug: Print the resolved prompt panel before invocation.
        console: Console for debug output.

    Returns:
        The ``(content, thinking, result)`` tuple from ``do_single_llm_call``.
    """

    prompt = system_prompt or (Path(__file__).parent / "prompts" / "prompt_bug_analysis.xml").read_text(
        encoding="utf-8"
    )
    prompt_template = ChatPromptTemplate.from_template(prompt)
    code_context = gather_files_for_context(
        code_python_file_globs
        + code_js_file_globs
        + code_frontend_file_globs
        + code_rust_file_globs
        + code_java_file_globs
    )
    return do_single_llm_call(
        chat_model=chat_model,
        system_prompt=prompt_template.format(code_context=code_context),
        user_input=user_input,
        env_info=env_info,
        display_format=display_format,
        debug=debug,
        console=console,
    )


def do_prompt_generation_agent(
    *,
    chat_model: BaseChatModel,
    user_input: str,
    system_prompt: str | None,
    debug: bool = True,
    console: Console | None = None,
) -> tuple[str, str, BaseMessage]:
    """Generate a refined prompt from the user's request using the meta-prompt template.

    Renders the meta-prompt (``prompts/meta_prompt.xml``) and delegates to
    ``do_single_llm_call``. Reasoning models are invoked without a system prompt.

    Args:
        chat_model: The chat model generating the prompt.
        user_input: The user's seed request.
        system_prompt: Optional override for the meta-prompt template.
        debug: Print the resolved prompt panel before invocation.
        console: Console for debug output.

    Returns:
        The ``(content, thinking, result)`` tuple from ``do_single_llm_call``.
    """

    prompt = system_prompt or (Path(__file__).parent / "prompts" / "meta_prompt.xml").read_text(encoding="utf-8")
    prompt_template = ChatPromptTemplate.from_template(prompt)
    if is_reasoning_model(chat_model):
        return do_single_llm_call(
            chat_model=chat_model,
            user_input=prompt_template.format(user_input=user_input),
            no_system_prompt=True,
            debug=debug,
            console=console,
        )
    else:
        return do_single_llm_call(
            chat_model=chat_model,
            system_prompt=prompt_template.format(user_input=""),
            user_input=user_input,
            debug=debug,
            console=console,
        )

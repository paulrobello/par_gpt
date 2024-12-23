"""Agents"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from langchain.agents import AgentExecutor, create_react_agent, create_tool_calling_agent
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

console = Console(stderr=True)


def do_single_llm_call(
    *,
    chat_model: BaseChatModel,
    user_input: str,
    image: str | None = None,
    system_prompt: str | None = None,
    no_system_prompt: bool = False,
    env_info: str | None = None,
    display_format: DisplayOutputFormat = DisplayOutputFormat.NONE,
    debug: bool,
    io: Console | None = None,
) -> tuple[str, BaseMessage]:
    if not io:
        io = Console(stderr=True)
    default_system_prompt = "<purpose>You are a helpful assistant. Try to be concise and brief unless the user requests otherwise. If an output_instructions section is provided, follow its instructions for output.</purpose>"

    chat_history: list[tuple[str, str | list[dict[str, Any]]]] = []
    if not no_system_prompt:
        chat_history.append(
            (
                "system",
                (system_prompt or default_system_prompt).strip() + "\n" + get_output_format_prompt(display_format),
            )
        )
        if env_info:
            chat_history.append(("user", env_info))

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
        io.print(Panel.fit(Pretty(chat_history_debug), title="GPT Prompt"))
    result = chat_model.invoke(chat_history, config=llm_run_manager.get_runnable_config(chat_model.name))  # type: ignore
    content = str(result.content).replace("```markdown", "").replace("```", "").strip()
    result.content = content
    return content, result


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
    io: Console | None = None,
):
    """React agent"""
    if not io:
        io = Console(stderr=True)
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
        io.print(Panel.fit(default_system_prompt, title="GPT Prompt"))
    result = agent_executor.invoke({"question": question}, config=llm_run_manager.get_runnable_config(chat_model.name))
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
    debug: bool = True,
    verbose: bool = False,
    io: Console | None = None,
):
    """Tool agent"""
    if image:
        raise ValueError("Image not supported for tool agent")

    if not io:
        io = Console(stderr=True)

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
    <instruction>If a tool returns an error message asking you to stop, do not make any additional requests and use the error message as the final answer.</instruction>
    <instruction>Use tools and the extra_context section to help answer the question.</instruction>
    <instruction>When doing a web search determine which of the results is best and only download content from that result.</instruction>
    <instruction>When creating code you MUST follow the rules in the code_rules section.</instruction>
"""
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
    <rule>Do NOT install any packages.</rule>
    <rule>NEVER execute code that could destroy data or otherwise harm the system or its data and files.</rule>
    <rule>The available_modules are already available and do not need to be imported.</rule>
    <rule>Do not include imports in your code reference the module name instead.</rule>
    <rule>If an "AbortedByUserError" is raised by a tool, return its message to the user as the final answer.</rule>
</repl_rules>
"""

    default_system_prompt += """
<code_rules>
    <rule>Assume python version is 3.11</rule>
    <rule>Ensure any web requests have a 10 second timeout.</rule>
    <rule>Ensure that encoding is set to "utf-8" for all file operations.</rule>
</code_rules>

{module_text}

{env_info}

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
    args = {"user_input": user_input, "module_text": module_text, "env_info": env_info}
    if debug:
        io.print(Panel.fit(prompt_template.format(**args, agent_scratchpad=""), title="GPT Prompt"))
    result = agent_executor.invoke(args, config=llm_run_manager.get_runnable_config(chat_model.name))
    # if debug:
    #     io.print(Panel.fit(Pretty(result), title="GPT Response))
    if isinstance(result["output"], str):
        content = result["output"]
    else:
        content = result["output"][0]["text"]
    content = content.replace("```markdown", "").replace("```", "").strip()
    return content, result


def do_code_review_agent(
    *,
    chat_model: BaseChatModel,
    env_info: str,
    user_input: str,
    system_prompt: str | None,
    display_format: DisplayOutputFormat,
    debug: bool = True,
    io: Console | None = None,
) -> tuple[str, BaseMessage]:
    """Code Agent"""

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
        io=io,
    )


def do_prompt_generation_agent(
    *,
    chat_model: BaseChatModel,
    user_input: str,
    system_prompt: str | None,
    debug: bool = True,
    io: Console | None = None,
) -> tuple[str, BaseMessage]:
    """Prompt Agent"""

    prompt = system_prompt or (Path(__file__).parent / "prompts" / "meta_prompt.xml").read_text(encoding="utf-8")
    prompt_template = ChatPromptTemplate.from_template(prompt)
    if chat_model.name and chat_model.name.startswith("o1"):
        return do_single_llm_call(
            chat_model=chat_model,
            user_input=prompt_template.format(user_input=user_input),
            no_system_prompt=True,
            debug=debug,
            io=io,
        )
    else:
        return do_single_llm_call(
            chat_model=chat_model,
            system_prompt=prompt_template.format(user_input=""),
            user_input=user_input,
            debug=debug,
            io=io,
        )

"""Agents"""

from __future__ import annotations

from langchain.agents import create_react_agent, AgentExecutor, create_tool_calling_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.tools import BaseTool
from rich.console import Console
from rich.panel import Panel


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
    result = agent_executor.invoke({"question": question})
    content = str(result["output"]).replace("```markdown", "").replace("```", "").strip()
    result["output"] = content
    return content, result


def do_tool_agent(
    *,
    chat_model: BaseChatModel,
    ai_tools: list[BaseTool],
    modules: list[str],
    env_info: str,
    question: str,
    system_prompt: str | None,
    image: str | None = None,
    max_iterations: int = 5,
    debug: bool = True,
    verbose: bool = False,
    io: Console | None = None,
):
    """Tool agent"""
    if not io:
        io = Console(stderr=True)
    if image:
        raise ValueError("Image not supported for tool agent")

    module_text = (
        "<available_modules>\n"
        + ("\n".join([f"    <module>{module}</module>" for module in modules]) + "\n")
        + "</available_modules>\n"
    )
    default_system_prompt = """
<role>You are a helpful assistant.</role>
<instructions>
    <instruction>Answer the users question, try to be concise and brief unless the user requests otherwise.</instruction>
    <instruction>Use tools and the "Extra Context" section to help answer the question.</instruction>
    <instruction>When doing a web search determine which of the results is best and only download content from that result.</instruction>
    <instruction>Think through all the steps needed to answer the question and make a plan before using tools.</instruction>
    <instruction>When creating and executing code you MUST follow the rules in the repl_rules section.</instruction>
    <repl_rules>
        <rule>Assume python version is 3.11</rule>
        <rule>Do NOT install any packages.</rule>
        <rule>Ensure any web requests have a 10 second timeout.</rule>
        <rule>Ensure that encoding is set to "utf-8" for all file operations.</rule>
        <rule>NEVER execute code that could destroy data or otherwise harm the system or its data and files.</rule>
        <rule>The available_modules are already available and do not need to be imported.</rule>
        <rule>If an "AbortedByUserError" is raised by a tool, return its message to the user as the final answer.</rule>
    </repl_rules>
</instructions>

{module_text}

{env_info}

<question>
{question}
</question>

<agent_scratchpad>
{agent_scratchpad}
</agent_scratchpad>
        """
    prompt = system_prompt or default_system_prompt
    if "agent_scratchpad" not in prompt:
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
    args = {"question": question, "module_text": module_text, "env_info": env_info}
    if debug:
        io.print(Panel.fit(prompt_template.format(**args, agent_scratchpad=""), title="GPT Prompt"))
    result = agent_executor.invoke(args)
    # if debug:
    #     io.print(Panel.fit(Pretty(result), title="GPT Response))
    if isinstance(result["output"], str):
        content = result["output"]
    else:
        content = result["output"][0]["text"]
    content = content.replace("```markdown", "").replace("```", "").strip()
    return content, result

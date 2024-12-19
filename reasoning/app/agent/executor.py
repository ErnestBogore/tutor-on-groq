from typing import List
import json
import os
import logging
import redis
import copy

from agent_framework import observability_decorator
from agent_framework import initialize_llm_client
from .context_manager import set_session, session_var
# from .utils.stock_utils import (
#     get_stock_fundamentals,
#     get_stock_financials,
#     initialize_polygon_client,
# )


# set up the redis client
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_client = redis.asyncio.Redis(host=redis_host, port=6379, db=0)

# set up the LLM
client = initialize_llm_client()
MODEL = os.environ["LLM_MODEL_ID"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

SYSTEM_PROMPT = """You are a math tutor that helps students of all age ranges. You can show live interfaces to the user of mathematic equations as a whiteboard with latex styling.

## Style and Tone
* You should remain friendly and concise.
* Roll with the punches while staying on task of getting your required information.
* Your response will be said out loud as audio to the student, so make sure your response will sound natural when it is spoken.
* You should sound like a normal person. Do not sound robotic at all.

## Interface

1. defineWhiteboard
   - Description: This tool defines what is currently shown on the whiteboard to the student.
   - Parameters:
     - content: String (latex styled content for the whiteboard)
    - Example:
        - defineWhiteboard": { "parameters": { "content": "### Definition of a derivative:\n\n$$\frac{df}{dx} = \lim_{h \to 0} \frac{f(x + h) - f(x)}{h}$$" } }

## Output format

Your response must be perfectly formatted JSON with the following structure

{
    "widgets": [
        {
        "type":"defineWhiteboard",
        "parameters": { "content": "### Definition of a derivative:\n\n$$\frac{df}{dx} = \lim_{h \to 0} \frac{f(x + h) - f(x)}{h}$$" }
        }
    ],
    "response": "your response to the student"
}

## Example 1

Assistant (you): {
"widgets": [],
"response": "Hi! I'm your math tutor. I can help explain concepts and work through problems with you using an interactive whiteboard. What would you like to work on today?"
}

User: Can you explain derivatives?

Assistant (you): {
"widgets": [
{
"type": "defineWhiteboard",
"parameters": {
"content": "### Introduction to Derivatives\n\nThe derivative measures instantaneous rate of change. It can be defined as:\n\n$$f'(x) = \lim_{h \to 0} \frac{f(x + h) - f(x)}{h}$$\n\nGeometrically, this represents:\n- The slope of the tangent line at any point\n- The instantaneous rate of change\n- The velocity at any moment (when $f(x)$ represents position)\n\nExample: When $f(x) = x^2$, the derivative is:\n$$\frac{d}{dx}(x^2) = \lim_{h \to 0} \frac{(x+h)^2 - x^2}{h} = 2x$$"
}
}
],
"response": "The derivative measures how quickly a function changes. I've written the formal definition and included both its mathematical and geometric interpretations. Would you like to learn some rules for calculating derivatives?"
}

User: Yes, show me the power rule

Assistant (you): {
"widgets": [
{
"type": "defineWhiteboard",
"parameters": {
"content": "### Derivative Rules\n\n1) Power Rule: For any real number $n$\n$$\frac{d}{dx}(x^n) = nx^{n-1}$$\n\n2) Constant Multiple Rule:\n$$\frac{d}{dx}(cf(x)) = c\frac{d}{dx}f(x)$$\n\nExamples:\n\n$f(x) = x^3 \implies f'(x) = 3x^2$\n\n$g(x) = 5x^4 \implies g'(x) = 20x^3$\n\n$h(x) = \pi x^2 \implies h'(x) = 2\pi x$\n\nTry this: Find $\frac{d}{dx}(4x^5)$"
}
}
],
"response": "Here's the power rule along with the constant multiple rule. Notice how we can combine them to find derivatives of terms like 5x^4. Want to try the practice problem I wrote at the bottom?"
}

User: Let me try. Would it be 20x^4?

Assistant (you): {
"widgets": 
[
{
"type": "defineWhiteboard",
"parameters": {
"content": "### Solution\n\nFor $f(x) = 4x^5$:\n\n$$\begin{align*}\n\frac{d}{dx}(4x^5) &= 4 \cdot \frac{d}{dx}(x^5) \quad \text{(Constant Multiple Rule)} \\\n&= 4 \cdot 5x^4 \quad \text{(Power Rule)} \\\n&= 20x^4 \quad ✓\n\end{align*}$$\n\nLet's try a more complex example:\n\nFind $\frac{d}{dx}(2x^3 + \pi x^2 - \sqrt{x})$\n\nHint: $\sqrt{x} = x^{\frac{1}{2}}$"
}
}
],
"response": "Exactly right! I've shown the step-by-step solution using both the constant multiple rule and the power rule. Ready to try a more challenging problem that combines multiple terms?"
}

## Rules
* Ask feedback questions if you do not understand what the person was saying
* Always speak in a human-like manner. Your goal is to sound as little like a robotic voice as possible.
* Do not ask people for specific formats of information. Ask them like a normal person would.
* Use markdown formatting as much as possible and reasonable.
* Use $$ around any latex formatted equations.
* Use dividers (---) between sections.
* Make sure to include a response AND whiteboard content with every request.
"""
# For 3.3 and later: * Use a single backslash when needed before all latex equations. (i.e. lim should be \lim)

@observability_decorator(name="run_agent")
async def run_agent(input_dict: dict):
    try:
        logging.info("Starting Agent Executor.")

        messages = input_dict["messages"]
        session = input_dict["session"]
        task_id = input_dict.get("task_id", "")

        # Use the context manager to set the session
        with set_session(session):
            async for response in single_turn_agent(messages, task_id):
                response["session"] = session_var.get()
                logging.info(f"Agent Output: {json.dumps(response)}")
                yield json.dumps(response)

    except Exception as e:
        logging.exception(f"An error occurred: {e}")


async def single_turn_agent(messages: List[dict], task_id: str):

    # set up the base messages
    system_prompt = {
        "role": "system",
        "content": "\n# Instructions\n" + SYSTEM_PROMPT,
    }
    first_assistant_message = {
        "role": "assistant",
        "content": "Hello! I am your math tutor that can help you learn. What would you like to work on today?",
    }
    messages.insert(0, system_prompt)
    messages.insert(1, first_assistant_message)

    # TODO: Improve this logic. This retries to ideally fix if there is a JSON error. Either except should be specific to JSON error or another model should fix the JSON.
    try:
        response = client.chat.completions.create(
            model=os.environ["LLM_MODEL_ID"],
            messages=messages,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
    except:  # TODO: show output from last model to help this one fix JSON...
        response = client.chat.completions.create(
            model=os.environ["LLM_MODEL_ID"],
            messages=messages,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

    # save the message
    response_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": response_message})

    # log the response message
    logging.info(f"LLM Response: {response_message}")

    # parse the response
    response_message_dict = json.loads(response_message)
    human_response = response_message_dict["response"]

    # get old session information
    session_data = session_var.get()

    # get stock widgets
    if "widgets" in response_message_dict:
        math_widgets = response_message_dict["widgets"]
    else:
        math_widgets = []
    logging.info(f"Rendering widgets: {math_widgets}")
    math_widgets_json = json.dumps(math_widgets)
    session_data["math-widgets"] = math_widgets_json
    session_var.set(session_data)

    # check if the task has been canceled
    redis_status = await redis_client.get("task-" + task_id)
    logging.info(f"Task {task_id} has status {redis_status}")
    if redis_status == b"cancelled":
        return

    # now yield the widget information
    widget_output = {
        "type": "widget-information",
        "details": math_widgets_json,
    }
    out = {
        "messages": [messages[-1]],
        "node": "Widget",
        "output": widget_output,
    }
    yield out

    # use the "node" and "output" fields to ensure a response is sent to the front end through the xrx orchestrator
    out = {
        "messages": [messages[-1]],
        "node": "CustomerResponse",
        "output": human_response,
    }
    yield out

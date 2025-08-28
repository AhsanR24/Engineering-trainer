import chainlit as cl
from dotenv import load_dotenv
import os

from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner, AsyncOpenAI,OpenAIChatCompletionsModel,set_tracing_disabled, RunConfig, set_default_openai_client 
from agents.exceptions import InputGuardrailTripwireTriggered
from pydantic import BaseModel, Field
import asyncio

import re

GREETINGS = {"hi", "hello", "hey", "salaam", "bonjour", "howdy", "good morning", "good evening"}

def is_greeting(text: str) -> bool:
    # Normalize input
    text = text.lower().strip()
    # Split into words using regex to handle punctuation
    words = set(re.findall(r'\b\w+\b', text))
    return any(greet in words for greet in GREETINGS)


_ = load_dotenv()


# Tracing disabled
set_tracing_disabled(disabled=True)

# LLM Service
external_client: AsyncOpenAI = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# LLM Model
llm_model: OpenAIChatCompletionsModel = OpenAIChatCompletionsModel(
    model="gemini-2.5-flash",
    openai_client=external_client
)


class EngineerTopicOutput(BaseModel):
    is_irrelevant: bool = Field(..., description="Is the question unrelated to mechatronics, avionics, or electrical engineering?")
    reasoning: str

guardrail_agent = Agent(
    name="Engineering Guardrail",
    instructions="Introduce yourself then Check if the user's question is NOT related to Mechatronics, Avionics, or Electrical Engineering.",
    output_type=EngineerTopicOutput,
    model=llm_model
)


# Engineer Specialization Agents
mechatronics_agent = Agent(
    name="Mechatronics Expert",
    handoff_description="Expert in mechatronics, combining mechanical, electrical, and computer systems.",
    instructions="You are an expert in Mechatronics Engineering. Respond clearly and helpfully. Support communication in English, Urdu, and French.",
    model=llm_model
)

avionics_agent = Agent(
    name="Avionics Expert",
    handoff_description="Expert in avionics and aircraft electronic systems.",
    instructions="You are an expert in Avionics Engineering. Respond clearly and helpfully. Support communication in English, Urdu, and French.",
    model=llm_model
)

electrical_agent = Agent(
    name="Electrical Engineering Expert",
    handoff_description="Expert in electrical circuits, power systems, and electronics.",
    instructions="You are an expert in Electrical Engineering. Respond clearly and helpfully. Support communication in English, Urdu, and French.",
    model=llm_model
)


async def engineer_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(EngineerTopicOutput)
    print("[Guardrail_function]", final_output)
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=final_output.is_irrelevant,
    )

engineer_trainer_agent = Agent(
    name="Engineer Trainer",
    instructions=(
        "You determine which engineering domain (Mechatronics, Avionics, Electrical) is best suited to respond. "
        "Also consider the language the user prefers (English, Urdu, or French)."
    ),
    handoffs=[mechatronics_agent, avionics_agent, electrical_agent],
    input_guardrails=[
        InputGuardrail(guardrail_function=engineer_guardrail),
    ],
    model=llm_model
)

GREETINGS = {"hi", "hello", "hey", "salaam", "bonjour", "howdy", "good morning", "good evening"}

@cl.on_message
async def handle_message(message: cl.Message):
    user_input = message.content

    if is_greeting(user_input):
        await cl.Message(
            content="👋 Hello! I'm your Engineering Trainer. Ask me anything about Mechatronics, Avionics, or Electrical Engineering."
        ).send()
        return
    
    try:
        result = await Runner.run(engineer_trainer_agent, message.content)
        await cl.Message(content=str(result.final_output)).send()
    except InputGuardrailTripwireTriggered:
        await cl.Message(
            content="❌ Your input was blocked because it's not related to Mechatronics, Avionics, or Electrical Engineering."
        ).send()
Comprehensive Guide to Creating AI Agents with OpenAI Agents SDK
Based on the information provided, I'll create a detailed, step-by-step guide on how to build AI agents using OpenAI's Agents SDK. This guide will walk you through the entire process from setup to advanced implementation patterns.

Table of Contents
Understanding AI Agents: Concepts and Architecture
Setting Up Your Development Environment
Creating Your First Basic Agent
Enhancing Agents with Tools
Structuring Agent Outputs
Implementing Agent Handoffs
Best Practices and Advanced Patterns
Testing and Deployment
Resources and Next Steps
Would you like me to proceed with this structure, or would you prefer a different focus or organization for the guide?


No I want you to provide me a detailed guide how to build an AI agent.


The user wants me to provide a detailed guide on how to build an AI agent without further discussion about the structure. I'll create a comprehensive guide based on the information provided in the tutorial, covering all aspects of building an AI agent using OpenAI's Agents SDK. I'll make it detailed and actionable, with code examples and explanations.


Comprehensive Guide to Building an AI Agent with OpenAI Agents SDK
1. Understanding AI Agents: Concepts and Architecture
AI agents are autonomous systems that can understand instructions, make decisions, and take actions to accomplish tasks. Unlike traditional AI models that simply respond to queries, agents can interact with external systems, use tools, and coordinate with other agents to solve complex problems.

Key Components of an AI Agent:
Core Language Model: The foundation that powers understanding and generation capabilities
Instructions: Defines the agent's behavior, personality, and limitations
Tools: Functions that extend the agent's capabilities beyond text generation
Handoffs: Mechanisms for transferring control between specialized agents
Guardrails: Safety measures that validate inputs and outputs
Agent Architecture Patterns:
Single-agent systems: One agent handles all tasks
Specialist agents: Multiple agents with specific expertise areas
Hierarchical systems: Coordinator agents delegate to specialist agents
Sequential workflows: Agents hand off control in a defined sequence
2. Setting Up Your Development Environment
Before building your first agent, you need to set up your environment:

Prerequisites:
Python 3.8+ installed
Basic understanding of async/await patterns in Python
OpenAI API key
Installation:
# Create and activate a virtual environment
python -m venv agents-env
source agents-env/bin/activate  # On Windows: agents-env\Scripts\activate

# Install required packages
pip install openai-agents python-dotenv
API Key Management:
# Create a .env file in your project directory
# Add your OpenAI API key to this file:
# OPENAI_API_KEY=your-api-key-here

# In your Python code:
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access your API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")
3. Creating Your First Basic Agent
Let's start by creating a simple agent:

from agents import Agent, Runner
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a basic agent
basic_agent = Agent(
    name="My First Agent",
    instructions="You are a helpful assistant that provides factual information.",
    model="gpt-4o"  # Optional: defaults to "gpt-4o" if not specified
)

# For Jupyter notebooks:
result = await Runner.run(basic_agent, "Hello! Can you tell me about AI agents?")
print(result.final_output)

# For Python scripts:
import asyncio

async def main():
    result = await Runner.run(basic_agent, "Hello! Can you tell me about AI agents?")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
Customizing Agent Behavior:
from agents import Agent, ModelSettings

# Create an agent with custom settings
advanced_agent = Agent(
    name="Advanced Assistant",
    instructions="""You are a professional, concise assistant who always provides
    accurate information. When you don't know something, clearly state that.
    Focus on giving actionable insights when answering questions.""",
    model="gpt-4o",
    model_settings=ModelSettings(
        temperature=0.3,  # Lower for more deterministic outputs (0.0-2.0)
        max_tokens=1024,  # Maximum length of response
    )
)
Writing Effective Instructions:
The instructions parameter is crucial for defining your agent's behavior. Here are best practices:

Define the role clearly: "You are a [specific role] who helps users with [specific tasks]."
Set boundaries: "You should not provide advice on [restricted topics]."
Establish tone and style: "Communicate in a friendly, conversational manner."
Define knowledge boundaries: "If asked about events after September 2021, explain that your knowledge has a cutoff date."
Specify output format preferences: "Use bullet points for lists and provide concise explanations."
Example of comprehensive instructions:

weather_instructions = """
You are a weather information assistant who helps users understand weather patterns and phenomena.

YOUR EXPERTISE:
- Explaining weather concepts and terminology
- Describing how different weather systems work
- Answering questions about climate and seasonal patterns
- Explaining the science behind weather events

LIMITATIONS:
- You cannot provide real-time weather forecasts for specific locations
- You don't have access to current weather data
- You should not make predictions about future weather events

STYLE:
- Use clear, accessible language that non-meteorologists can understand
- Include interesting weather facts when relevant
- Be enthusiastic about meteorology and climate science
"""
4. Enhancing Agents with Tools
Tools are what transform agents from simple conversational assistants into systems that can take meaningful actions. The OpenAI Agents SDK supports three types of tools:

4.1 Hosted Tools:
These run on OpenAI's servers and provide built-in capabilities:

from agents import Agent, Runner, WebSearchTool

# Create a research assistant with web search capability
research_assistant = Agent(
    name="Research Assistant",
    instructions="""You are a research assistant that helps users find and summarize information.
    When asked about a topic:
    1. Search the web for relevant, up-to-date information
    2. Synthesize the information into a clear, concise summary
    3. Structure your response with headings and bullet points when appropriate
    4. Always cite your sources at the end of your response
    
    If the information might be time-sensitive or rapidly changing, mention when the search was performed.
    """,
    tools=[WebSearchTool()]
)

# Customized search tool with location context
location_aware_search = WebSearchTool(
    user_location="San Francisco, CA",  # Provides geographic context for local search queries
    search_context_size=3  # Number of search results to consider in the response
)
4.2 Function Tools:
These allow you to extend your agent with any Python function:

import os
import requests
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from agents import Agent, Runner, function_tool

@dataclass
class WeatherInfo:
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float
    pressure: int
    location_name: str
    rain_1h: Optional[float] = None
    visibility: Optional[int] = None

@function_tool
def get_weather(lat: float, lon: float) -> str:
    """Get the current weather for a specified location using OpenWeatherMap API.

    Args:
        lat: Latitude of the location (-90 to 90)
        lon: Longitude of the location (-180 to 180)
    """
    # Get API key from environment variables
    WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

    # Build URL with parameters
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract weather data from the response
        weather_info = WeatherInfo(
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            description=data["weather"][0]["description"],
            wind_speed=data["wind"]["speed"],
            pressure=data["main"]["pressure"],
            location_name=data["name"],
            visibility=data.get("visibility"),
            rain_1h=data.get("rain", {}).get("1h"),
        )

        # Build the response string
        weather_report = f"""
        Weather in {weather_info.location_name}:
        - Temperature: {weather_info.temperature}°C (feels like {weather_info.feels_like}°C)
        - Conditions: {weather_info.description}
        - Humidity: {weather_info.humidity}%
        - Wind speed: {weather_info.wind_speed} m/s
        - Pressure: {weather_info.pressure} hPa
        """
        return weather_report

    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {str(e)}"

# Create a weather assistant
weather_assistant = Agent(
    name="Weather Assistant",
    instructions="""You are a weather assistant that can provide current weather information.
    
    When asked about weather, use the get_weather tool to fetch accurate data.
    If the user doesn't specify a country code and there might be ambiguity,
    ask for clarification (e.g., Paris, France vs. Paris, Texas).
    
    Provide friendly commentary along with the weather data, such as clothing suggestions
    or activity recommendations based on the conditions.
    """,
    tools=[get_weather]
)
4.3 Agents as Tools:
This pattern allows you to use agents themselves as tools, enabling hierarchical structures:

# Specialist agents
note_taking_agent = Agent(
    name="Note Manager",
    instructions="You help users take and organize notes efficiently.",
    # In a real application, this agent would have note-taking tools
)

task_management_agent = Agent(
    name="Task Manager",
    instructions="You help users manage tasks, deadlines, and priorities.",
    # In a real application, this agent would have task management tools
)

# Coordinator agent that uses specialists as tools
productivity_assistant = Agent(
    name="Productivity Assistant",
    instructions="""You are a productivity assistant that helps users organize their work and personal life.
    
    For note-taking questions or requests, use the note_taking tool.
    For task and deadline management, use the task_management tool.
    
    Help the user decide which tool is appropriate based on their request,
    and coordinate between different aspects of productivity.
    """,
    tools=[
        note_taking_agent.as_tool(
            tool_name="note_taking",
            tool_description="For taking, organizing, and retrieving notes and information"
        ),
        task_management_agent.as_tool(
            tool_name="task_management",
            tool_description="For managing tasks, setting deadlines, and tracking priorities"
        )
    ]
)
5. Structuring Agent Outputs
For more reliable applications, you can define exactly what data structure you want your agent to return:

from pydantic import BaseModel
from typing import List, Optional

# Define person data model
class Person(BaseModel):
    name: str
    role: Optional[str]
    contact: Optional[str]

# Define meeting data model
class Meeting(BaseModel):
    date: str
    time: str
    location: Optional[str]
    duration: Optional[str]

# Define task data model
class Task(BaseModel):
    description: str
    assignee: Optional[str]
    deadline: Optional[str]
    priority: Optional[str]

# Define the complete email data model
class EmailData(BaseModel):
    subject: str
    sender: Person
    recipients: List[Person]
    main_points: List[str]
    meetings: List[Meeting]
    tasks: List[Task]
    next_steps: Optional[str]

# Create an email extraction agent with structured output
email_extractor = Agent(
    name="Email Extractor",
    instructions="""You are an assistant that extracts structured information from emails.
    
    When given an email, carefully identify:
    - Subject and main points
    - People mentioned (names, roles, contact info)
    - Meetings (dates, times, locations)
    - Tasks or action items (with assignees and deadlines)
    - Next steps or follow-ups
    
    Extract this information as structured data. If something is unclear or not mentioned,
    leave those fields empty rather than making assumptions.
    """,
    output_type=EmailData,  # This tells the agent to return data in EmailData format
)
The output_type parameter works with various types:

# For simple lists
agent_with_list_output = Agent(
    name="List Generator",
    instructions="Generate lists of items based on the user's request.",
    output_type=list[str],  # Returns a list of strings
)

# For dictionaries
agent_with_dict_output = Agent(
    name="Dictionary Generator",
    instructions="Create key-value pairs based on the input.",
    output_type=dict[str, int],  # Returns a dictionary with string keys and integer values
)

# For simple primitive types
agent_with_bool_output = Agent(
    name="Decision Maker",
    instructions="Answer yes/no questions with True or False.",
    output_type=bool,  # Returns a boolean
)
6. Implementing Agent Handoffs
Handoffs allow one agent to delegate control to another specialized agent:

6.1 Basic Handoffs:
from agents import Agent, handoff, Runner

# Create specialist agents
billing_agent = Agent(
    name="Billing Agent",
    instructions="""You are a billing specialist who helps customers with payment issues.
    Focus on resolving billing inquiries, subscription changes, and refund requests.
    If asked about technical problems or account settings, explain that you specialize
    in billing and payment matters only.""",
)

technical_agent = Agent(
    name="Technical Agent",
    instructions="""You are a technical support specialist who helps with product issues.
    Assist users with troubleshooting, error messages, and how-to questions.
    Focus on resolving technical problems only.""",
)

# Create a triage agent that can hand off to specialists
triage_agent = Agent(
    name="Customer Service",
    instructions="""You are the initial customer service contact who helps direct
    customers to the right specialist.
    
    If the customer has billing or payment questions, hand off to the Billing Agent.
    If the customer has technical problems or how-to questions, hand off to the Technical Agent.
    For general inquiries or questions about products, you can answer directly.
    
    Always be polite and helpful, and ensure a smooth transition when handing off to specialists.""",
    handoffs=[billing_agent, technical_agent],  # Direct handoff to specialist agents
)
6.2 Customized Handoffs:
from agents import Agent, handoff, RunContextWrapper
from datetime import datetime

# Create an agent that handles account-related questions
account_agent = Agent(
    name="Account Management",
    instructions="""You help customers with account-related issues such as
    password resets, account settings, and profile updates.""",
)

# Custom handoff callback function
async def log_account_handoff(ctx: RunContextWrapper[None]):
    print(f"[LOG] Account handoff triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # In a real app, you might log to a database or alert a human supervisor

# Create a triage agent with customized handoffs
enhanced_triage_agent = Agent(
    name="Enhanced Customer Service",
    instructions="""You are the initial customer service contact who directs
    customers to the right specialist.
    
    If the customer has billing or payment questions, hand off to the Billing Agent.
    If the customer has technical problems, hand off to the Technical Agent.
    If the customer needs to change account settings, hand off to the Account Management agent.
    For general inquiries, you can answer directly.""",
    handoffs=[
        billing_agent,  # Basic handoff
        handoff(  # Customized handoff
            agent=account_agent,
            on_handoff=log_account_handoff,  # Callback function
            tool_name_override="escalate_to_account_team",  # Custom tool name
            tool_description_override="Transfer the customer to the account management team for help with account settings, password resets, etc.",
        ),
        technical_agent,  # Basic handoff
    ],
)
6.3 Passing Data During Handoffs:
from pydantic import BaseModel
from typing import Optional
from agents import Agent, handoff, RunContextWrapper

# Define the data structure to pass during handoff
class EscalationData(BaseModel):
    reason: str
    priority: Optional[str]
    customer_tier: Optional[str]

# Handoff callback that processes the escalation data
async def process_escalation(ctx: RunContextWrapper, input_data: EscalationData):
    print(f"[ESCALATION] Reason: {input_data.reason}")
    print(f"[ESCALATION] Priority: {input_data.priority}")
    print(f"[ESCALATION] Customer tier: {input_data.customer_tier}")

    # You might use this data to prioritize responses, alert human agents, etc.

# Create an escalation agent
escalation_agent = Agent(
    name="Escalation Agent",
    instructions="""You handle complex or sensitive customer issues that require
    special attention. Always address the customer's concerns with extra care and detail.""",
)

# Create a service agent that can escalate with context
service_agent = Agent(
    name="Service Agent",
    instructions="""You are a customer service agent who handles general inquiries.
    
    For complex issues, escalate to the Escalation Agent and provide:
    - The reason for escalation
    - Priority level (Low, Normal, High, Urgent)
    - Customer tier if mentioned (Standard, Premium, VIP)""",
    handoffs=[
        handoff(
            agent=escalation_agent,
            on_handoff=process_escalation,
            input_type=EscalationData,
        )
    ],
)
7. Best Practices and Advanced Patterns
7.1 Agent Design Principles:
Single Responsibility: Each agent should have a clear, focused purpose
Clear Instructions: Be specific about what the agent should and shouldn't do
Appropriate Tools: Equip agents with only the tools they need
Graceful Fallbacks: Handle edge cases and unexpected inputs
Consistent Personality: Maintain a consistent tone and style
7.2 Advanced Agent Patterns:
Chain-of-Thought Agents:
cot_agent = Agent(
    name="Reasoning Agent",
    instructions="""You solve complex problems by breaking them down into steps.
    
    When faced with a complex question:
    1. First, identify what information you need and what steps to take
    2. Work through each step methodically, showing your reasoning
    3. If you're uncertain about a step, explain your uncertainty
    4. After working through all steps, provide your final answer
    
    Always show your complete reasoning process before giving the final answer."""
)
Multi-Agent Systems:
# Create a system of specialized agents
data_analyst = Agent(
    name="Data Analyst",
    instructions="You analyze data and provide insights based on statistical analysis.",
    # Would have data analysis tools in a real implementation
)

content_writer = Agent(
    name="Content Writer",
    instructions="You create engaging content based on data and insights.",
    # Would have content generation tools in a real implementation
)

editor = Agent(
    name="Editor",
    instructions="You review and improve content for clarity, accuracy, and style.",
    # Would have editing tools in a real implementation
)

# Workflow coordinator
report_generator = Agent(
    name="Report Generator",
    instructions="""You coordinate the creation of data-driven reports by:
    1. First using the data_analyst to analyze the provided data
    2. Then using the content_writer to create a draft report based on the analysis
    3. Finally using the editor to review and improve the draft
    
    Your job is to manage this workflow and ensure a high-quality final report.""",
    tools=[
        data_analyst.as_tool(
            tool_name="analyze_data",
            tool_description="Analyze data and provide insights"
        ),
        content_writer.as_tool(
            tool_name="write_content",
            tool_description="Create engaging content based on data and insights"
        ),
        editor.as_tool(
            tool_name="edit_content",
            tool_description="Review and improve content for clarity, accuracy, and style"
        )
    ]
)
7.3 Error Handling and Resilience:
from agents import Agent, function_tool
import traceback

@function_tool
def risky_operation(input_data: str) -> str:
    """A function that might fail under certain conditions.
    
    Args:
        input_data: The input to process
    """
    try:
        # Potentially risky operation
        if "trigger_error" in input_data:
            raise ValueError("Simulated error for demonstration")
        
        return f"Successfully processed: {input_data}"
    except Exception as e:
        error_details = traceback.format_exc()
        return f"Error: {str(e)}\nDetails: {error_details}"

resilient_agent = Agent(
    name="Resilient Agent",
    instructions="""You perform operations that might occasionally fail.
    
    When using the risky_operation tool:
    1. If it succeeds, explain the result to the user
    2. If it fails, explain what went wrong and suggest alternatives
    3. Never expose raw error messages to the user; translate them into user-friendly terms
    
    Always maintain a helpful tone, even when errors occur.""",
    tools=[risky_operation]
)
8. Testing and Deployment
8.1 Testing Agents:
import unittest
from agents import Agent, Runner

class TestWeatherAgent(unittest.TestCase):
    async def test_weather_response_format(self):
        # Create a test agent with a mock weather tool
        @function_tool
        def mock_weather(lat: float, lon: float) -> str:
            """Mock weather tool for testing"""
            return """
            Weather in Test City:
            - Temperature: 20.0°C (feels like 19.5°C)
            - Conditions: clear sky
            - Humidity: 65%
            - Wind speed: 3.5 m/s
            - Pressure: 1015 hPa
            """
        
        test_agent = Agent(
            name="Test Weather Agent",
            instructions="You provide weather information.",
            tools=[mock_weather]
        )
        
        # Run the agent with a test query
        result = await Runner.run(test_agent, "What's the weather in Test City?")
        
        # Assert expected patterns in the response
        self.assertIn("Temperature", result.final_output)
        self.assertIn("°C", result.final_output)
        self.assertIn("Humidity", result.final_output)

if __name__ == "__main__":
    unittest.main()
8.2 Deployment Considerations:
Environment Management:

Use environment variables for API keys and configuration
Create separate configurations for development, testing, and production
Performance Optimization:

Use appropriate model sizes based on complexity needs
Implement caching for repeated queries
Consider batching requests when possible
Monitoring and Logging:

Log all agent interactions for debugging and improvement
Monitor usage patterns and error rates
Implement alerting for critical failures
Scaling:

Use asynchronous processing for handling multiple requests
Implement rate limiting to manage API usage
Consider serverless deployment for variable workloads
9. Resources and Next Steps
9.1 Further Learning:
Explore the OpenAI API documentation
Study the OpenAI Cookbook for advanced patterns
Join the OpenAI Developer Forum for community support
9.2 Advanced Topics to Explore:
Streaming Responses: Implementing real-time updates from agents
Tracing and Observability: Debugging complex agent systems
Multi-Agent Orchestration: Coordinating teams of specialized agents
Context Management: Maintaining conversation state across interactions
Guardrails: Ensuring safe and appropriate agent behavior
9.3 Project Ideas:
Personal Research Assistant: Create an agent that can search the web, summarize articles, and generate reports
Customer Support System: Build a multi-agent system for handling different types of customer inquiries
Data Analysis Assistant: Develop an agent that can analyze data, generate visualizations, and explain insights
Content Creation Pipeline: Create a system of agents for brainstorming, drafting, editing, and publishing content
Personal Productivity System: Build agents for task management, note-taking, and scheduling
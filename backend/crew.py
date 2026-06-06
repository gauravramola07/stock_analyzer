import os
from dotenv import load_dotenv
from crewai import Crew, Process, LLM
from agents import create_agents
from tasks import create_tasks

load_dotenv()

async def run_analysis(ticker: str):
    # Using openrouter/ prefix for OpenRouter compatibility
    model_name = os.getenv('OPENAI_MODEL_NAME', 'stepfun/step-3.7-flash:free')
    
    llm = LLM(
        model=f"openrouter/{model_name}",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=0.1,
        max_retries=5,
        timeout=300
    )

    agents = create_agents(llm)
    tasks = create_tasks(ticker, *agents)

    crew = Crew(
        agents=list(agents),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        # OpenRouter free tier is very strict. 1 RPM is safest.
        rpm_limit=1 
    )

    result = await crew.kickoff_async(inputs={"ticker": ticker})
    return result

import os
import json
import asyncio
from dotenv import load_dotenv
from crewai import Crew, Process, LLM
from agents import create_agents
from tasks import create_phase1_tasks, create_phase2_tasks
from prefetch import prefetch_all
from assembly import assemble_final_result

load_dotenv()


def _get_llm():
    api_base = os.getenv("OPENAI_API_BASE", "https://inference-api.nousresearch.com/v1")
    raw_model = os.getenv("OPENAI_MODEL_NAME", "stepfun/step-3.7-flash:free")
    model_path = raw_model if raw_model.startswith("openai/") else f"openai/{raw_model}"
    return LLM(
        model=model_path,
        api_key=os.getenv("OPENAI_API_KEY", "YOUR_API_KEY"),
        base_url=api_base,
        temperature=0.1,
        max_retries=2,
    )


def _get_task_output(task):
    if not task.output:
        return ""
    output = task.output
    if hasattr(output, "raw"):
        return str(output.raw)
    return str(output)


async def run_analysis(ticker: str, step_callback=None, log_queue=None):
    llm = _get_llm()
    agents = create_agents(llm)
    data_researcher, news_researcher, data_analyst, risk_manager, financial_expert = agents

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "prefetch", "status": "running"})})
        log_queue.put_nowait({"event": "log", "data": f"[System] Pre-fetching data for {ticker}..."})

    pre_fetched = await prefetch_all(ticker)

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "prefetch", "status": "done"})})
        log_queue.put_nowait({"event": "log", "data": "[System] Data pre-fetch complete. Starting parallel agent analysis..."})

    phase1_tasks = create_phase1_tasks(ticker, pre_fetched, data_researcher, news_researcher, data_analyst)
    data_task, news_task, analysis_task = phase1_tasks

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "data", "status": "running"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "news", "status": "running"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "analysis", "status": "running"})})

    data_crew = Crew(
        agents=[data_researcher], tasks=[data_task],
        process=Process.sequential, verbose=False,
        step_callback=step_callback, cache=True,
    )
    news_crew = Crew(
        agents=[news_researcher], tasks=[news_task],
        process=Process.sequential, verbose=False,
        step_callback=step_callback, cache=True,
    )
    analysis_crew = Crew(
        agents=[data_analyst], tasks=[analysis_task],
        process=Process.sequential, verbose=False,
        step_callback=step_callback, cache=True,
    )

    await asyncio.gather(
        data_crew.kickoff_async(inputs={"ticker": ticker}),
        news_crew.kickoff_async(inputs={"ticker": ticker}),
        analysis_crew.kickoff_async(inputs={"ticker": ticker}),
    )

    phase1_outputs = {
        "data": _get_task_output(data_task),
        "news": _get_task_output(news_task),
        "analysis": _get_task_output(analysis_task),
    }

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "data", "status": "done"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "news", "status": "done"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "analysis", "status": "done"})})
        log_queue.put_nowait({"event": "log", "data": "[System] Phase 1 complete. Starting risk and expert analysis..."})

    phase2_tasks = create_phase2_tasks(ticker, pre_fetched, phase1_outputs, risk_manager, financial_expert)

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "risk", "status": "running"})})

    phase2_crew = Crew(
        agents=[risk_manager, financial_expert],
        tasks=phase2_tasks,
        process=Process.sequential,
        verbose=False,
        step_callback=step_callback,
        cache=True,
    )

    await phase2_crew.kickoff_async(inputs={"ticker": ticker})

    phase1_outputs["risk"] = _get_task_output(phase2_tasks[0])
    phase1_outputs["expert"] = _get_task_output(phase2_tasks[1])

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "risk", "status": "done"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "expert", "status": "running"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "expert", "status": "done"})})
        log_queue.put_nowait({"event": "log", "data": "[System] All agents complete. Assembling final result..."})

    final_result = assemble_final_result(ticker, pre_fetched, phase1_outputs)

    return final_result
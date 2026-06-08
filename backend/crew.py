import os
import json
import asyncio
import traceback
from dotenv import load_dotenv
from crewai import Crew, Process, LLM
from agents import create_agents, AGENT_VERBOSE
from tasks import create_phase1_tasks, create_risk_task, create_expert_task
from prefetch import prefetch_all
from assembly import assemble_final_result

load_dotenv()

# Monkey patch CrewAI LLM to strip cache_breakpoint for non-Anthropic models
# This avoids "property cache_breakpoint is unsupported" errors on models like Groq, Stepfun, etc.
original_format_messages_for_provider = LLM._format_messages_for_provider

def patched_format_messages_for_provider(self, messages):
    formatted = original_format_messages_for_provider(self, messages)
    if not self.is_anthropic:
        cleaned = []
        for msg in formatted:
            if isinstance(msg, dict):
                cleaned.append({k: v for k, v in msg.items() if k != "cache_breakpoint"})
            else:
                cleaned.append(msg)
        return cleaned
    return formatted

LLM._format_messages_for_provider = patched_format_messages_for_provider

# Provider-specific default API bases
PROVIDER_BASES = {
    "groq": "https://api.groq.com/openai/v1",
    "xai": "https://api.x.ai/v1",
    "nous": "https://inference-api.nousresearch.com/v1",
    "openai": "https://api.openai.com/v1",
}


def _detect_provider_base(raw_model: str, env_base: str, provider_hint: str = "") -> str:
    """Auto-detect the correct API base URL based on model name prefix."""
    model_lower = raw_model.lower()
    # If model starts with a known provider prefix, use that provider's base
    for prefix, base in PROVIDER_BASES.items():
        if model_lower.startswith(prefix + "/"):
            return base
    # If provider hint is given and no prefix in model, use hint's base
    if provider_hint and provider_hint in PROVIDER_BASES:
        return PROVIDER_BASES[provider_hint]
    # Otherwise use the env-provided base
    return env_base


def _normalize_model_path(raw_model: str) -> str:
    """Normalize model path for litellm: strip known provider prefixes and add openai/."""
    # Strip provider prefix if present (litellm handles routing via base_url)
    for prefix in PROVIDER_BASES:
        if raw_model.lower().startswith(prefix + "/"):
            raw_model = raw_model[len(prefix) + 1:]
    # Add openai/ prefix for litellm compatibility
    if not raw_model.startswith("openai/"):
        raw_model = f"openai/{raw_model}"
    return raw_model


def _get_free_llm():
    api_base = os.getenv("OPENAI_API_BASE", "https://inference-api.nousresearch.com/v1")
    raw_model = os.getenv("OPENAI_MODEL_NAME", "stepfun/step-3.7-flash:free")
    model_path = _normalize_model_path(raw_model)
    return LLM(
        model=model_path,
        api_key=os.getenv("OPENAI_API_KEY", "YOUR_API_KEY"),
        base_url=api_base,
        temperature=0.1,
        max_retries=5,  # Increased to automatically retry on 429 rate limits
    )


def _get_fast_llm():
    raw_model = os.getenv("GROQ_MODEL_NAME", os.getenv("XAI_MODEL_NAME", "llama-3.1-8b-instant"))
    env_base = os.getenv("GROQ_API_BASE", os.getenv("XAI_API_BASE", "https://api.groq.com/openai/v1"))
    api_base = _detect_provider_base(raw_model, env_base, "groq")
    model_path = _normalize_model_path(raw_model)
    api_key = os.getenv("GROQ_API_KEY", os.getenv("XAI_API_KEY", "YOUR_API_KEY"))

    print(f"[fast_llm] model={model_path}, base_url={api_base}")

    return LLM(
        model=model_path,
        api_key=api_key,
        base_url=api_base,
        temperature=0.1,
        max_retries=5,  # Increased to automatically retry on 429 rate limits
    )


def _get_task_output(task):
    if not task.output:
        return ""
    output = task.output
    if hasattr(output, "raw"):
        return str(output.raw)
    return str(output)


async def run_analysis(ticker: str, step_callback=None, log_queue=None):
    fast_llm = _get_fast_llm()
    free_llm = _get_free_llm()
    # Pass ticker to create_agents so agent goals contain the actual ticker, not {ticker}
    agents = create_agents(fast_llm, free_llm, ticker=ticker)
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

    # Disable LLM cache at crew level — prefetch layer already handles data caching.
    # cache=True can return stale LLM responses if price/indicator values round identically across runs.
    data_crew = Crew(
        agents=[data_researcher], tasks=[data_task],
        process=Process.sequential, verbose=AGENT_VERBOSE,
        step_callback=step_callback, cache=False,
    )
    news_crew = Crew(
        agents=[news_researcher], tasks=[news_task],
        process=Process.sequential, verbose=AGENT_VERBOSE,
        step_callback=step_callback, cache=False,
    )
    analysis_crew = Crew(
        agents=[data_analyst], tasks=[analysis_task],
        process=Process.sequential, verbose=AGENT_VERBOSE,
        step_callback=step_callback, cache=False,
    )

    # Run phase 1 crews in parallel with error resilience
    # return_exceptions=True prevents one crew failure from crashing the entire pipeline
    results = await asyncio.gather(
        data_crew.kickoff_async(inputs={"ticker": ticker}),
        news_crew.kickoff_async(inputs={"ticker": ticker}),
        analysis_crew.kickoff_async(inputs={"ticker": ticker}),
        return_exceptions=True,
    )

    # Handle partial failures — extract output where successful, placeholder where failed
    phase1_outputs = {}
    crew_names = ["data", "news", "analysis"]
    tasks_list = [data_task, news_task, analysis_task]

    for i, (name, task) in enumerate(zip(crew_names, tasks_list)):
        result = results[i]
        if isinstance(result, Exception):
            print(f"[WARNING] {name} crew failed: {result}")
            if log_queue:
                log_queue.put_nowait({"event": "log", "data": f"[System] {name} crew failed — using fallback data."})
            phase1_outputs[name] = "{}"
        else:
            phase1_outputs[name] = _get_task_output(task)

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "data", "status": "done"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "news", "status": "done"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "analysis", "status": "done"})})
        log_queue.put_nowait({"event": "log", "data": "[System] Phase 1 complete. Starting risk and expert analysis..."})

    # --- Phase 2: Run risk first, then expert with actual risk output injected ---
    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "risk", "status": "running"})})

    risk_task_obj = create_risk_task(ticker, pre_fetched, phase1_outputs, risk_manager)

    risk_crew = Crew(
        agents=[risk_manager], tasks=[risk_task_obj],
        process=Process.sequential, verbose=AGENT_VERBOSE,
        step_callback=step_callback, cache=False,
    )

    try:
        await asyncio.wait_for(
            risk_crew.kickoff_async(inputs={"ticker": ticker}),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        print(f"[WARNING] Risk crew timed out for {ticker}")
        if log_queue:
            log_queue.put_nowait({"event": "log", "data": "[System] Risk analysis timed out — using available data."})
    except Exception as e:
        print(f"[WARNING] Risk crew failed: {e}")
        if log_queue:
            log_queue.put_nowait({"event": "log", "data": f"[System] Risk analysis failed — using fallback data."})

    risk_output = _get_task_output(risk_task_obj) if risk_task_obj.output else "{}"

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "risk", "status": "done"})})
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "expert", "status": "running"})})

    # Build expert task with actual risk output directly injected (not via context=[])
    expert_task_obj = create_expert_task(ticker, pre_fetched, phase1_outputs, risk_output, financial_expert)

    expert_crew = Crew(
        agents=[financial_expert], tasks=[expert_task_obj],
        process=Process.sequential, verbose=AGENT_VERBOSE,
        step_callback=step_callback, cache=False,
    )

    try:
        await asyncio.wait_for(
            expert_crew.kickoff_async(inputs={"ticker": ticker}),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        print(f"[WARNING] Expert crew timed out for {ticker}")
        if log_queue:
            log_queue.put_nowait({"event": "log", "data": "[System] Expert analysis timed out — using available data."})
    except Exception as e:
        print(f"[WARNING] Expert crew failed: {e}")
        if log_queue:
            log_queue.put_nowait({"event": "log", "data": f"[System] Expert analysis failed — assembling result with available data."})

    # Build clean all_outputs dict (avoid reusing phase1_outputs for clarity)
    all_outputs = {
        "data":     phase1_outputs.get("data", "{}"),
        "news":     phase1_outputs.get("news", "{}"),
        "analysis": phase1_outputs.get("analysis", "{}"),
        "risk":     risk_output,
        "expert":   _get_task_output(expert_task_obj) if expert_task_obj.output else "{}",
    }

    if log_queue:
        log_queue.put_nowait({"event": "phase", "data": json.dumps({"step": "expert", "status": "done"})})
        log_queue.put_nowait({"event": "log", "data": "[System] All agents complete. Assembling final result..."})

    final_result = assemble_final_result(ticker, pre_fetched, all_outputs)

    return final_result
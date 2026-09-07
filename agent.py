"""OpenAI Agents SDK brain for mailbox triage."""

from agents import Agent, Runner

agent = Agent(
    name="Caspian Inbox Analyst",
    instructions=(
        "You are an executive inbox assistant. Classify email importance, extract actionable tasks, "
        "and identify deadlines, interview steps, candidates, and shortlist decisions. "
        "Be concise and practical. Return plain text suitable for a messaging channel."
    ),
)


def ask(text: str) -> str:
    result = Runner.run_sync(agent, text or "Summarize the latest important inbox items.", max_turns=8)
    return (result.final_output or "").strip() or "No answer available."

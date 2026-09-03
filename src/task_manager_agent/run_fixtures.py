"""Run the fixture messages through the graph and eyeball the results.

Usage (from repo root):
    python -m task_manager_agent.run_fixtures
"""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

load_dotenv()

# tests/ isn't part of the installed package, so make it importable
# regardless of the caller's CWD (python -m only puts CWD on sys.path).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.sample_messages import SAMPLE_MESSAGES

from task_manager_agent.graph import build_graph
from task_manager_agent.models import MessageState

EXCERPT_LEN = 40


def _excerpt(text: str, n: int = EXCERPT_LEN) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= n else text[:n] + "…"


def main() -> None:
    graph = build_graph()

    n_pass = 0
    n_review = 0
    n_fail = 0
    n_error = 0
    total = len(SAMPLE_MESSAGES)

    for fixture in SAMPLE_MESSAGES:
        msg_id = fixture.get("id", "?")
        try:
            state = MessageState(
                id=fixture["id"],
                timestamp=fixture["timestamp"],
                sender=fixture["sender"],
                group_id=fixture["group_id"],
                raw_text=fixture["raw_text"],
            )

            result = graph.invoke(state)

            needs_review = result.get("needs_review", False)
            is_task = result.get("is_task")
            title = result.get("title")
            due_date = result.get("due_date")
            assignee = result.get("assignee")
            priority = result.get("priority")

            excerpt = _excerpt(fixture["raw_text"])

            if needs_review:
                n_review += 1
                print(
                    f"{msg_id}\tREVIEW\t{excerpt}\t"
                    f"error={result.get('error')!r}"
                )
                continue

            mismatches = []
            if is_task != fixture.get("expected_is_task"):
                mismatches.append(
                    f"is_task: expected={fixture.get('expected_is_task')!r} got={is_task!r}"
                )
            if title != fixture.get("expected_title"):
                mismatches.append(
                    f"title: expected={fixture.get('expected_title')!r} got={title!r}"
                )
            if due_date != fixture.get("expected_due_date"):
                mismatches.append(
                    f"due_date: expected={fixture.get('expected_due_date')!r} got={due_date!r}"
                )
            if assignee != fixture.get("expected_assignee"):
                mismatches.append(
                    f"assignee: expected={fixture.get('expected_assignee')!r} got={assignee!r}"
                )
            if priority != fixture.get("expected_priority"):
                mismatches.append(
                    f"priority: expected={fixture.get('expected_priority')!r} got={priority!r}"
                )

            if mismatches:
                n_fail += 1
                print(f"{msg_id}\tFAIL\t{excerpt}")
                for m in mismatches:
                    print(f"    {m}")
            else:
                n_pass += 1
                print(f"{msg_id}\tPASS\t{excerpt}")

        except Exception as e:
            n_error += 1
            print(f"{msg_id}\tERROR\t{e!r}")
            continue

    print("-" * 60)
    print(
        f"{n_pass}/{total} passed, {n_review} needs_review, "
        f"{n_fail} failed, {n_error} errored"
    )


if __name__ == "__main__":
    main()

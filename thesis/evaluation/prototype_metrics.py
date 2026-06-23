"""
Prototype Evaluation Metrics

Tracks task performance during prototype demonstrations:
- Time-to-first-action (how quickly participants respond to feedback)
- Task completion rates
- Routing accuracy (did they route to the correct team?)
- Confidence ratings
- Pre/post comparison (current workflow vs Odradek)
"""

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class TaskAttempt:
    """A single task performed by a participant during the demo."""
    participant_id: str
    task_id: str  # e.g., "T1_triage_nps", "T2_route_complaint", "T3_create_rule"
    task_description: str
    started_at: datetime = None
    completed_at: datetime = None
    completed: bool = False
    correct_routing: bool = None  # for routing tasks
    errors: int = 0
    confidence: int = None  # 1-5 self-reported confidence
    notes: str = ""

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class PrePostComparison:
    """Pre/post comparison of current workflow vs Odradek."""
    participant_id: str
    # Current workflow (self-reported, pre-demo)
    current_time_to_action_hours: float = None  # avg hours from feedback to first action
    current_tools_count: int = None  # number of tools used
    current_weekly_triage_hours: float = None  # hours/week on manual triage
    current_feedback_sources: int = None  # number of feedback sources
    current_satisfaction: int = None  # 1-5 satisfaction with current process
    # After Odradek demo (post-demo)
    expected_time_to_action_hours: float = None
    expected_weekly_triage_hours: float = None
    odradek_satisfaction: int = None  # 1-5 satisfaction with Odradek
    would_adopt: bool = None
    adoption_barriers: list = field(default_factory=list)


# --- Scenario Definition ---

DEMO_SCENARIOS = {
    "S1_morning_triage": {
        "description": "You arrive Monday morning. Overnight: 47 NPS responses, 12 support tickets, 3 social mentions, 2 app reviews. Process them.",
        "tasks": [
            {"id": "T1_identify_critical", "description": "Identify the most critical signals requiring immediate attention", "expected_time_sec": 120},
            {"id": "T2_route_complaint", "description": "Route a high-severity complaint to the correct team", "expected_time_sec": 60},
            {"id": "T3_create_rule", "description": "Create an automation rule for similar future complaints", "expected_time_sec": 90},
        ]
    },
    "S2_trend_detection": {
        "description": "NPS has dropped 8 points over two weeks. Investigate and respond.",
        "tasks": [
            {"id": "T4_identify_cause", "description": "Use the dashboard to identify the cause of the NPS drop", "expected_time_sec": 180},
            {"id": "T5_segment_analysis", "description": "Determine which customer segment is most affected", "expected_time_sec": 120},
            {"id": "T6_action_plan", "description": "Create an action plan using insights and rules", "expected_time_sec": 150},
        ]
    },
    "S3_feedback_loop": {
        "description": "Close the loop: a VIP customer left negative feedback last week. Follow up.",
        "tasks": [
            {"id": "T7_find_signal", "description": "Locate the original feedback signal and its history", "expected_time_sec": 60},
            {"id": "T8_review_actions", "description": "Review what actions were taken (if any) via the action log", "expected_time_sec": 45},
            {"id": "T9_close_loop", "description": "Mark the insight as resolved and log the follow-up action", "expected_time_sec": 60},
        ]
    }
}


@dataclass
class PrototypeEvaluation:
    """Container for all prototype evaluation data."""
    task_attempts: list[TaskAttempt] = field(default_factory=list)
    comparisons: list[PrePostComparison] = field(default_factory=list)

    def add_attempt(self, attempt: TaskAttempt):
        self.task_attempts.append(attempt)

    def add_comparison(self, comparison: PrePostComparison):
        self.comparisons.append(comparison)

    def task_completion_rate(self) -> dict:
        """Completion rate per task and overall."""
        by_task = {}
        for scenario in DEMO_SCENARIOS.values():
            for task in scenario["tasks"]:
                tid = task["id"]
                attempts = [a for a in self.task_attempts if a.task_id == tid]
                completed = [a for a in attempts if a.completed]
                by_task[tid] = {
                    "description": task["description"],
                    "attempts": len(attempts),
                    "completed": len(completed),
                    "rate": len(completed) / max(len(attempts), 1),
                    "expected_time_sec": task["expected_time_sec"]
                }

        total = len(self.task_attempts)
        total_completed = sum(1 for a in self.task_attempts if a.completed)
        return {
            "overall_rate": total_completed / max(total, 1),
            "overall_completed": total_completed,
            "overall_total": total,
            "per_task": by_task
        }

    def time_to_action_summary(self) -> dict:
        """Average time per task across participants."""
        by_task = {}
        for a in self.task_attempts:
            if a.duration_seconds is not None and a.completed:
                by_task.setdefault(a.task_id, []).append(a.duration_seconds)

        return {
            tid: {
                "mean_sec": round(statistics.mean(times), 1),
                "median_sec": round(statistics.median(times), 1),
                "stdev_sec": round(statistics.stdev(times), 1) if len(times) > 1 else 0,
                "n": len(times)
            }
            for tid, times in by_task.items()
        }

    def pre_post_summary(self) -> dict:
        """Summarize pre/post comparison data."""
        if not self.comparisons:
            return {"n": 0, "message": "No comparison data"}

        pre_triage = [c.current_weekly_triage_hours for c in self.comparisons
                      if c.current_weekly_triage_hours is not None]
        post_triage = [c.expected_weekly_triage_hours for c in self.comparisons
                       if c.expected_weekly_triage_hours is not None]
        pre_tta = [c.current_time_to_action_hours for c in self.comparisons
                   if c.current_time_to_action_hours is not None]
        post_tta = [c.expected_time_to_action_hours for c in self.comparisons
                    if c.expected_time_to_action_hours is not None]
        adopt = [c.would_adopt for c in self.comparisons if c.would_adopt is not None]

        result = {"n": len(self.comparisons)}

        if pre_triage and post_triage:
            result["triage_hours"] = {
                "current_mean": round(statistics.mean(pre_triage), 1),
                "expected_mean": round(statistics.mean(post_triage), 1),
                "reduction_pct": round((1 - statistics.mean(post_triage) / statistics.mean(pre_triage)) * 100, 1)
            }
        if pre_tta and post_tta:
            result["time_to_action"] = {
                "current_mean_hours": round(statistics.mean(pre_tta), 1),
                "expected_mean_hours": round(statistics.mean(post_tta), 1),
                "reduction_pct": round((1 - statistics.mean(post_tta) / statistics.mean(pre_tta)) * 100, 1)
            }
        if adopt:
            result["adoption_willingness"] = round(sum(adopt) / len(adopt) * 100, 1)

        return result

    def export_report(self) -> str:
        """Generate thesis-ready evaluation report."""
        lines = ["# Prototype Evaluation Report\n"]

        # Task completion
        completion = self.task_completion_rate()
        lines.append("## Task Completion\n")
        lines.append(f"**Overall completion rate**: {completion['overall_rate']:.1%} "
                     f"({completion['overall_completed']}/{completion['overall_total']})\n")
        lines.append("| Task | Completed | Rate | Expected Time |")
        lines.append("|------|-----------|------|---------------|")
        for tid, data in completion["per_task"].items():
            lines.append(f"| {tid} | {data['completed']}/{data['attempts']} | "
                        f"{data['rate']:.0%} | {data['expected_time_sec']}s |")
        lines.append("")

        # Time performance
        times = self.time_to_action_summary()
        if times:
            lines.append("## Task Times\n")
            lines.append("| Task | Mean (s) | Median (s) | SD | N |")
            lines.append("|------|----------|------------|-----|---|")
            for tid, data in times.items():
                lines.append(f"| {tid} | {data['mean_sec']} | {data['median_sec']} | "
                            f"{data['stdev_sec']} | {data['n']} |")
            lines.append("")

        # Pre/post comparison
        prepost = self.pre_post_summary()
        if prepost["n"] > 0:
            lines.append("## Pre/Post Comparison\n")
            lines.append(f"**Participants**: {prepost['n']}\n")
            if "triage_hours" in prepost:
                t = prepost["triage_hours"]
                lines.append(f"**Weekly triage hours**: {t['current_mean']}h → {t['expected_mean']}h "
                           f"({t['reduction_pct']}% reduction)")
            if "time_to_action" in prepost:
                t = prepost["time_to_action"]
                lines.append(f"**Time to first action**: {t['current_mean_hours']}h → {t['expected_mean_hours']}h "
                           f"({t['reduction_pct']}% reduction)")
            if "adoption_willingness" in prepost:
                lines.append(f"**Would adopt**: {prepost['adoption_willingness']}%")

        return "\n".join(lines)


# --- Event-log telemetry (Phase F1) ---------------------------------------
# The Odradek app records an `events` table (see supabase/migrations). Export it
# to a JSON array and summarise the timed-task telemetry here. This complements the
# facilitator-recorded TaskAttempt data with objective in-app measurements.

def load_event_log(path) -> list[dict]:
    """Load an exported events JSON array (rows from the public.events table)."""
    return json.loads(Path(path).read_text())


def summarize_event_log(events: list[dict]) -> dict:
    """Time-to-action and action counts from app telemetry.

    Rows are expected to have: event_type, duration_ms, created_at, metadata.
    `insight_status_advanced` rows carry duration_ms = time from detection to action.
    """
    by_type: dict = {}
    for e in events:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1

    tta_ms = [e["duration_ms"] for e in events
              if e.get("event_type") == "insight_status_advanced" and e.get("duration_ms")]

    summary = {
        "event_counts": by_type,
        "rules_created": by_type.get("rule_created", 0),
        "actions_approved": by_type.get("action_approved", 0),
        "actions_rejected": by_type.get("action_rejected", 0),
        "outcomes_measured": by_type.get("outcome_measured", 0),
        "learnings_shown": by_type.get("learnings_shown", 0),
    }
    if tta_ms:
        secs = [ms / 1000 for ms in tta_ms]
        summary["time_to_action_sec"] = {
            "mean": round(statistics.mean(secs), 1),
            "median": round(statistics.median(secs), 1),
            "stdev": round(statistics.stdev(secs), 1) if len(secs) > 1 else 0,
            "n": len(secs),
        }
    return summary


if __name__ == "__main__":
    print("Prototype Evaluation Metrics")
    print("=" * 50)
    print(f"Scenarios defined: {len(DEMO_SCENARIOS)}")
    for sid, scenario in DEMO_SCENARIOS.items():
        print(f"\n  {sid}: {scenario['description'][:60]}...")
        for task in scenario["tasks"]:
            print(f"    - {task['id']}: {task['description']}")

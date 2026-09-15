"""Feedback and Lesson management engine (Sections 92-99)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import yaml
from pathlib import Path


class Lesson:
    """Represents an analytical rule or learning item derived from feedback."""

    def __init__(
        self,
        lesson_id: str,
        feedback_id: str,
        run_id: str,
        lesson_type: str,  # query_feedback, retrieval_feedback, analysis_feedback, output_feedback
        user_feedback: str,
        derived_lesson: str,
        scope: Optional[Dict[str, Any]] = None,
        status: str = "candidate",  # candidate, accepted, rejected, retired (Section 94)
    ):
        self.lesson_id = lesson_id
        self.feedback_id = feedback_id
        self.run_id = run_id
        self.lesson_type = lesson_type
        self.user_feedback = user_feedback
        self.derived_lesson = derived_lesson
        self.scope = scope or {}
        self.status = status if status in ("candidate", "accepted", "rejected", "retired") else "candidate"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "feedback_id": self.feedback_id,
            "run_id": self.run_id,
            "lesson_type": self.lesson_type,
            "user_feedback": self.user_feedback,
            "derived_lesson": self.derived_lesson,
            "scope": self.scope,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Lesson:
        return cls(
            lesson_id=data["lesson_id"],
            feedback_id=data["feedback_id"],
            run_id=data["run_id"],
            lesson_type=data["lesson_type"],
            user_feedback=data["user_feedback"],
            derived_lesson=data["derived_lesson"],
            scope=data.get("scope", {}),
            status=data.get("status", "candidate"),
        )


class LessonLedger:
    """Ledger persisting and querying lessons across workspace."""

    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path
        self.lessons: Dict[str, Lesson] = {}
        self.load()

    def load(self) -> None:
        if self.ledger_path.exists():
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "lessons" in data:
                    for l_data in data["lessons"]:
                        lesson = Lesson.from_dict(l_data)
                        self.lessons[lesson.lesson_id] = lesson

    def save(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"lessons": [l.to_dict() for l in self.lessons.values()]}
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    def add_lesson(self, lesson: Lesson) -> None:
        self.lessons[lesson.lesson_id] = lesson
        self.save()

    def get_applicable_lessons(
        self,
        analysis_type: Optional[str] = None,
        only_accepted: bool = False,
    ) -> List[Lesson]:
        """Returns lessons applicable to the current context adhering to Section 95 rules."""
        matched = []
        for l in self.lessons.values():
            if only_accepted and l.status != "accepted":
                continue
            if l.status == "retired" or l.status == "rejected":
                continue

            l_type = l.scope.get("analysis_type")
            if l_type is None or analysis_type is None or l_type == analysis_type:
                matched.append(l)

        return matched

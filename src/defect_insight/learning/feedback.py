"""User feedback recorder and candidate lesson generator (Sections 92, 93, 99)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional
from defect_insight.learning.lessons import Lesson, LessonLedger


class FeedbackRecorder:
    """Records feedback and extracts candidate lessons without auto-accepting."""

    def __init__(self, ledger: LessonLedger):
        self.ledger = ledger

    def record_feedback(
        self,
        run_id: str,
        feedback_type: str,
        user_feedback: str,
        derived_lesson: str,
        scope: Optional[Dict[str, Any]] = None,
    ) -> Lesson:
        """Records a user or agent reflection feedback item as a candidate lesson (Section 94)."""
        f_idx = len(self.ledger.lessons) + 1
        feedback_id = f"FB-{f_idx:04d}"
        lesson_id = f"LES-{f_idx:04d}"

        lesson = Lesson(
            lesson_id=lesson_id,
            feedback_id=feedback_id,
            run_id=run_id,
            lesson_type=feedback_type,
            user_feedback=user_feedback,
            derived_lesson=derived_lesson,
            scope=scope or {},
            status="candidate",  # Strictly candidate by default (Section 94, 99)
        )
        self.ledger.add_lesson(lesson)
        return lesson

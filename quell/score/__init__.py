"""Quell Score — mutation-verified coverage metrics and badge generation."""
from quell.score.badge import generate_badge
from quell.score.calculator import FileScore, ProjectScore, calculate_score
from quell.score.tracker import get_score_history, record_score

__all__ = [
    "calculate_score",
    "ProjectScore",
    "FileScore",
    "generate_badge",
    "record_score",
    "get_score_history",
]

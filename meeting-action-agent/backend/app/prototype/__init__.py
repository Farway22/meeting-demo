"""最小原型：会议文本 → 任务列表 + 个人待办。"""

__all__ = ["call_llm", "normalize_participants", "run_pipeline"]


def __getattr__(name: str):
    if name == "run_pipeline":
        from app.prototype.meeting_pipeline import run_pipeline

        return run_pipeline
    if name == "normalize_participants":
        from app.prototype.meeting_pipeline import normalize_participants

        return normalize_participants
    if name == "call_llm":
        from app.prototype.llm import call_llm

        return call_llm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Quell GitHub integration — PR comments, App webhook, Actions support."""
__all__ = ["format_pr_comment", "post_or_update_pr_comment"]


def __getattr__(name: str) -> object:
    if name == "format_pr_comment":
        from quell.github.formatter import format_pr_comment
        return format_pr_comment
    if name == "post_or_update_pr_comment":
        from quell.github.pr_commenter import post_or_update_pr_comment
        return post_or_update_pr_comment
    raise AttributeError(f"module 'quell.github' has no attribute {name!r}")

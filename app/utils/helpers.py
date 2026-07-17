"""General helper utilities."""


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "-")

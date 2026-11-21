"""Tiny JSX replacement: h("div", {"class": "p-4"}, child, ...) -> HTML string."""
from html import escape

VOID = {"img", "br", "hr", "input", "meta", "link"}


def h(tag, attrs=None, *children):
    attrs = attrs or {}
    parts = []
    for k, v in attrs.items():
        if v is None or v is False:
            continue
        k = k.rstrip("_").replace("_", "-") if k != "class_" else "class"
        parts.append(f' {k}' if v is True else f' {k}="{escape(str(v), quote=True)}"')
    open_tag = f"<{tag}{''.join(parts)}"
    if tag in VOID:
        return open_tag + " />"
    return open_tag + ">" + "".join(_render(c) for c in children) + f"</{tag}>"


def _render(c):
    if c is None or c is False:
        return ""
    if isinstance(c, (list, tuple)):
        return "".join(_render(x) for x in c)
    return c if isinstance(c, Raw) else escape(str(c))


class Raw(str):
    """Pre-rendered HTML (output of h()) is wrapped so it is not escaped twice."""


_h = h
def h(tag, attrs=None, *children):  # noqa: F811
    return Raw(_h(tag, attrs, *children))

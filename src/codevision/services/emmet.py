from __future__ import annotations

import re


class EmmetExpansionService:
    """Minimal Emmet-like expansion for simple HTML snippets."""

    @staticmethod
    def _expand_tag(tag_spec: str) -> list[str]:
        text = tag_spec.strip()
        if not text:
            return []

        match = re.fullmatch(r"([A-Za-z][\w-]*)(?:#([A-Za-z0-9_-]+))?(?:\.([A-Za-z0-9_-]+))?(?:\[(.*)\])?(?:\*(\d+))?", text)
        if match is None:
            return [f"<{text}></{text}>"]

        tag_name, _id, _class, _attrs, repeat = match.groups()
        count = int(repeat) if repeat is not None else 1
        if count <= 0:
            return []

        attrs = []
        if _id:
            attrs.append(f'id="{_id}"')
        if _class:
            attrs.append(f'class="{_class}"')
        if _attrs:
            attrs.append(_attrs)
        attrs_text = " " + " ".join(attrs) if attrs else ""
        item = f"<{tag_name}{attrs_text}></{tag_name}>"
        return [item for _ in range(count)]

    def expand(self, abbreviation: str) -> str | None:
        text = abbreviation.strip()
        if not text:
            return None

        if ">" not in text:
            if "*" in text:
                fragment = text.split("*", 1)
                if len(fragment) == 2 and fragment[0].strip():
                    tag = fragment[0].strip()
                    try:
                        count = int(fragment[1])
                    except ValueError:
                        return None
                    children = self._expand_tag(f"{tag}*{count}")
                    return "\n".join(children) if children else None
            return None

        parts = [part.strip() for part in text.split(">") if part.strip()]
        if not parts:
            return None

        parent = self._expand_tag(parts[0])
        if not parent:
            return None

        parent_tag = parts[0].split("*", 1)[0].split("[", 1)[0].split(".", 1)[0].split("#", 1)[0]
        child_items: list[str] = []
        for part in parts[1:]:
            child_items.extend(self._expand_tag(part))

        if not child_items:
            return None

        inner = "\n".join(f"    {item}" for item in child_items)
        return f"<{parent_tag}>\n{inner}\n</{parent_tag}>"


_default_service = EmmetExpansionService()


def expand_abbreviation(abbreviation: str) -> str | None:
    return _default_service.expand(abbreviation)

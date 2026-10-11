"""Expand a small supported subset of Emmet-style HTML abbreviations."""

from __future__ import annotations

import re


class EmmetExpansionService:
    """Convert supported tag abbreviations into simple HTML fragments.

    The implementation intentionally supports a narrow syntax focused on tag
    names, one id, one class, raw attributes, repetition, and child nesting.
    """

    @staticmethod
    def _expand_tag(tag_spec: str) -> list[str]:
        """Expand one tag specification, including optional repetition.

        Recognized pieces are a tag name, optional ``#id``, optional
        ``.class``, optional bracketed attributes, and optional ``*count``.
        A non-matching non-empty specification is emitted as a literal tag
        name. A non-positive repetition count produces no tags.

        Args:
            tag_spec: Single tag abbreviation to parse.

        Returns:
            A list of generated opening-and-closing tag strings.
        """
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
        """Expand a supported abbreviation or return ``None`` if unsupported.

        A simple repeated tag such as ``li*3`` becomes one line per tag. A
        nested abbreviation separated by ``>`` wraps the expanded child tags
        in the first parent tag. Empty input, invalid repetition counts, and
        nested forms without usable parent or child tags are rejected.

        Args:
            abbreviation: Emmet-like abbreviation supplied by the editor.

        Returns:
            Generated HTML text, or ``None`` when no supported expansion can
            be produced.
        """
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
    """Expand an abbreviation using the module's shared service instance.

    Args:
        abbreviation: Emmet-like abbreviation to expand.

    Returns:
        Expanded HTML or ``None`` when the abbreviation is unsupported.
    """
    return _default_service.expand(abbreviation)

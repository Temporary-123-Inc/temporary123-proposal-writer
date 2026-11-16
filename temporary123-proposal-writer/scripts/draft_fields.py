"""Locate and red-highlight editable draft fields without flattening Word runs.

Uses the ElementTree-compatible API shared by stdlib XML and python-docx's lxml.
No network, document rendering or dependency installation is performed here.
"""
from copy import deepcopy
import re


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
FIELD_PATTERN = re.compile(r"\[[^\[\]\r\n]{1,300}\]|\{\{[^{}\r\n]{1,100}\}\}|\b(?:TBD|TODO)\b", re.I)
NUMERIC_CITATION = re.compile(r"\[\s*\d+(?:\s*[-\u2013,;]\s*\d+)*\s*\]")
TEXT_PART = re.compile(r"word/(?:document|header\d+|footer\d+|footnotes|endnotes)\.xml$")


def field_matches(text):
    """Return supported draft markers, excluding ordinary numeric citations."""
    return [m for m in FIELD_PATTERN.finditer(text) if not NUMERIC_CITATION.fullmatch(m.group())]


def _ancestor(element, parents, tag):
    element = parents.get(element)
    while element is not None:
        if element.tag == W + tag:
            return element
        element = parents.get(element)
    return None


def _paragraph_segments(paragraph, parents):
    """Keep textboxes' nested paragraphs separate from their outer paragraph."""
    segments, texts, offset = [], [], 0
    for element in paragraph.iter():
        if element.tag not in (W + "t", W + "tab", W + "br", W + "cr"):
            continue
        if _ancestor(element, parents, "p") is not paragraph:
            continue
        text = (element.text or "") if element.tag == W + "t" else ("\t" if element.tag == W + "tab" else "\n")
        run = _ancestor(element, parents, "r")
        if text and run is not None:
            segments.append((element, run, offset, offset + len(text)))
            texts.append(text)
            offset += len(text)
    return "".join(texts), segments


def _red(run):
    properties = run.find(W + "rPr")
    if properties is None:
        return False
    highlight = properties.find(W + "highlight")
    return highlight is not None and highlight.get(W + "val") == "red"


def _set_red(run):
    properties = run.find(W + "rPr")
    if properties is None:
        properties = run.makeelement(W + "rPr", {})
        run.insert(0, properties)
    highlight = properties.find(W + "highlight")
    if highlight is None:
        highlight = properties.makeelement(W + "highlight", {})
        properties.append(highlight)
    highlight.set(W + "val", "red")
    color = properties.find(W + "color")
    if color is None:
        color = properties.makeelement(W + "color", {})
        properties.append(color)
    color.attrib.clear()
    color.set(W + "val", "000000")


def inspect_fields(root, part="word/document.xml"):
    """Find every occurrence and its red-highlight status, without guessing pages."""
    parents = {child: parent for parent in root.iter() for child in parent}
    found = []
    for number, paragraph in enumerate(root.iter(W + "p"), 1):
        text, segments = _paragraph_segments(paragraph, parents)
        for match in field_matches(text):
            covered = [run for _, run, start, end in segments if start < match.end() and end > match.start()]
            found.append({"field": match.group(), "part": part, "paragraph": number,
                          "red_highlighted": bool(covered) and all(_red(run) for run in covered)})
    return found


def highlight_fields(root):
    """Apply red highlight only to marker spans, preserving run styles and XML.

    Runs are split inside their existing parent, so bookmarks, hyperlinks,
    pictures and field structures remain in place. Nested textbox paragraphs are
    handled before their containing paragraphs. Existing non-marker formatting
    is left untouched. Returns the number of recognized field occurrences.
    """
    parents = {child: parent for parent in root.iter() for child in parent}
    count = 0
    for paragraph in reversed(list(root.iter(W + "p"))):
        text, segments = _paragraph_segments(paragraph, parents)
        matches = field_matches(text)
        count += len(matches)
        if not matches:
            continue
        by_run = {}
        for element, run, start, end in segments:
            local = [(max(start, m.start()) - start, min(end, m.end()) - start)
                     for m in matches if start < m.end() and end > m.start()]
            if local:
                by_run.setdefault(run, {})[element] = local
        for run, affected in by_run.items():
            parent = parents.get(run)
            if parent is None:
                continue
            properties = run.find(W + "rPr")
            pieces = []
            for child in run:
                if child.tag == W + "rPr":
                    continue
                ranges = affected.get(child)
                if not ranges or child.tag != W + "t":
                    pieces.append((bool(ranges), deepcopy(child)))
                    continue
                value = child.text or ""
                boundaries = sorted({0, len(value)} | {x for pair in ranges for x in pair})
                for start, end in zip(boundaries, boundaries[1:]):
                    if end <= start:
                        continue
                    item = deepcopy(child)
                    item.text = value[start:end]
                    if item.text[0].isspace() or item.text[-1].isspace():
                        item.set(XML_SPACE, "preserve")
                    pieces.append((any(a <= start and end <= b for a, b in ranges), item))
            replacements, previous = [], None
            for red, child in pieces:
                if previous is None or red != previous:
                    replacement = run.makeelement(run.tag, dict(run.attrib))
                    if properties is not None:
                        replacement.append(deepcopy(properties))
                    if red:
                        _set_red(replacement)
                    replacements.append(replacement)
                    previous = red
                replacements[-1].append(child)
            index = list(parent).index(run)
            parent.remove(run)
            for offset, replacement in enumerate(replacements):
                parent.insert(index + offset, replacement)
    return count

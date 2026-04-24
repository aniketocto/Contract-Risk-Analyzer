import re
from typing import Optional


# ---------------------------------------------------------------------------
# Section / clause heading patterns — ordered from most specific to broadest
# ---------------------------------------------------------------------------
_SECTION_PATTERNS = [
    # "Article 1 – Title" / "Article I. Title"
    re.compile(
        r'^(?:ARTICLE|Article)\s+'
        r'(?P<num>[IVXLCDM]+|\d+)'
        r'[\s.:–\-]*\s*(?P<title>.*)$'
    ),
    # "Section 1.2 – Something"
    re.compile(
        r'^(?:SECTION|Section)\s+'
        r'(?P<num>\d+(?:\.\d+)*)'
        r'[\s.:–\-]*\s*(?P<title>.*)$'
    ),
    # "Clause 3.1: ..."
    re.compile(
        r'^(?:CLAUSE|Clause)\s+'
        r'(?P<num>\d+(?:\.\d+)*)'
        r'[\s.:–\-]*\s*(?P<title>.*)$'
    ),
    # "1. Title" or "1.  Title" (top-level numbered heading — one integer)
    # Title must start with uppercase and can contain letters, spaces,
    # punctuation, parentheses, digits, etc.
    re.compile(
        r'^(?P<num>\d+)\.\s+(?P<title>[A-Z][^\n]{2,})$'
    ),
    # "1.1  Some text" / "1.1.2  Some text"  (sub-clause with decimals)
    re.compile(
        r'^(?P<num>\d+\.\d+(?:\.\d+)*)\s+(?P<title>.+)$'
    ),
    # "(a) / (b) / (i) / (ii)  lettered or roman sub-items"
    re.compile(
        r'^\((?P<num>[a-z]+|[ivxlcdm]+|\d+)\)\s+(?P<title>.+)$'
    ),
]


def _classify_level(num_str: str) -> int:
    """
    Decide the nesting depth (0 = top section, 1 = clause, 2 = sub-clause …)
    from the numbering token.
    """
    # Roman-numeral articles → level 0
    if re.fullmatch(r'[IVXLCDM]+', num_str):
        return 0
    # Single integer like "3" → level 0
    if re.fullmatch(r'\d+', num_str):
        return 0
    # Decimal like "3.1" → level 1, "3.1.2" → level 2, …
    if re.fullmatch(r'\d+(?:\.\d+)+', num_str):
        return num_str.count('.')
    # Lower-roman numerals "(i)", "(ii)", etc. → level 3
    # Use an explicit whitelist to avoid false positives (e.g. "c", "d", "l")
    _COMMON_ROMAN = {
        'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
        'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx',
    }
    if num_str in _COMMON_ROMAN:
        return 3
    # Lettered items "(a)", "(b)", "(c)" → level 2
    if re.fullmatch(r'[a-z]', num_str):
        return 2
    return 1


def _try_match(line: str) -> Optional[dict]:
    """
    Try every pattern against *line*.  Return the first match as
    {"num": str, "title": str, "level": int}  or None.
    """
    for pat in _SECTION_PATTERNS:
        m = pat.match(line)
        if m:
            num = m.group('num')
            title = m.group('title').strip()
            return {"num": num, "title": title, "level": _classify_level(num)}
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def structuring_agent(raw_text: str) -> dict:
    """
    Parse *raw_text* into a hierarchical list of sections → clauses.

    Handles diverse contract numbering styles:
      • "Article I / Article 1" headings
      • "Section 1.2" headings
      • "Clause 3.1:" headings
      • Bare numbered headings ("3. Limitation of Liability")
      • Decimal sub-clauses ("1.1 Some text …")
      • Lettered / roman sub-items "(a) …", "(ii) …"
      • Plain paragraph fallback

    Returns
    -------
    dict  with key ``"sections"`` — a list of section dicts, each containing:
        - ``id``      : original numbering token (e.g. "3", "3.1", "(a)")
        - ``title``   : section / clause heading (may be empty)
        - ``text``    : body text belonging to this item
        - ``level``   : nesting depth (0 = top section, 1 = clause, 2 = sub)
        - ``children``: list of child clause dicts (same shape, recursive)

    A flat convenience key ``"clauses"`` is also returned — a list of every
    leaf-level clause dict (id + full text) for backward compatibility.
    """

    # --- Step 1: Normalize whitespace ---
    text = raw_text.replace('\r\n', '\n').replace('\r', '\n').strip()
    lines = text.split('\n')

    # --- Step 2: Parse lines into an ordered list of "blocks" ---
    blocks: list[dict] = []          # each: {num, title, level, body_lines}
    current_block: Optional[dict] = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            # Blank line — store paragraph break inside current block
            if current_block is not None:
                current_block['body_lines'].append('')
            continue

        match = _try_match(line)
        if match:
            # Flush previous block
            if current_block is not None:
                blocks.append(current_block)
            current_block = {
                'num': match['num'],
                'title': match['title'],
                'level': match['level'],
                'body_lines': [],
            }
            # If the pattern captured a title that IS the clause body
            # (no separate heading), keep it as the first body line too
            # only when level > 0 and no separate title exists.
        else:
            if current_block is not None:
                current_block['body_lines'].append(line)
            else:
                # Text before any heading — create an implicit block
                current_block = {
                    'num': 'P0',
                    'title': '',
                    'level': 0,
                    'body_lines': [line],
                }

    if current_block is not None:
        blocks.append(current_block)

    # --- Step 3: Build hierarchy (sections → clauses → sub-clauses) ---
    sections: list[dict] = []
    flat_clauses: list[dict] = []     # backward-compat flat list

    def _make_node(block: dict) -> dict:
        body = '\n'.join(block['body_lines']).strip()
        title = block['title'].strip()

        # Combine title and body:
        # For "Clause 2.2: The text here" patterns, the actual clause text
        # is captured in 'title'.  If body also exists, we need BOTH.
        if title and body:
            display_text = title + '\n' + body
        elif title:
            display_text = title
        else:
            display_text = body

        return {
            'id': block['num'],
            'title': title,
            'text': display_text,
            'level': block['level'],
            'children': [],
        }

    # We use a simple approach: find the right parent for each node by
    # looking at the existing tree structure.  For each node, walk up the
    # tree to find the nearest ancestor whose level is strictly less than
    # the current node's level, and attach as a child.

    def _find_parent_and_attach(node: dict):
        """Attach *node* to the correct place in the sections tree."""
        level = node['level']

        if level == 0 or not sections:
            sections.append(node)
            return

        # Walk the last section's rightmost spine to find the right parent.
        # The parent must have a level < node's level.
        last_sec = sections[-1]

        if level <= last_sec['level']:
            # Same or higher level than the last section → new top-level
            sections.append(node)
            return

        # Descend the rightmost spine of last_sec
        parent = last_sec
        while parent['children']:
            candidate = parent['children'][-1]
            if candidate['level'] < level:
                parent = candidate
            else:
                break

        # Now 'parent' has level < node level → attach here
        if parent['level'] < level:
            parent['children'].append(node)
        else:
            # Sibling: attach to the same parent as 'parent'
            # This means we attach to the section itself
            sections[-1]['children'].append(node)

    for block in blocks:
        node = _make_node(block)
        _find_parent_and_attach(node)

    # --- Step 4: Build flat clause list for backward compat ---
    def _collect_leaves(node: dict):
        if not node['children']:
            # Leaf — build combined text
            full_text = node['text']
            flat_clauses.append({'id': node['id'], 'text': full_text})
        else:
            # If the node itself has body text, emit it too
            if node['text'] and node['text'] != node['title']:
                flat_clauses.append({'id': node['id'], 'text': node['text']})
            for child in node['children']:
                _collect_leaves(child)

    for sec in sections:
        _collect_leaves(sec)

    # --- Step 5: Fallback — if we parsed nothing useful, split by paragraph ---
    if not sections:
        paragraphs = text.split('\n')
        for idx, para in enumerate(paragraphs):
            clean = para.strip()
            if clean:
                node = {
                    'id': f'P{idx + 1}',
                    'title': '',
                    'text': clean,
                    'level': 0,
                    'children': [],
                }
                sections.append(node)
                flat_clauses.append({'id': node['id'], 'text': clean})

    return {
        'sections': sections,
        'clauses': flat_clauses,
    }
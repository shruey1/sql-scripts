import re

# ————————
# SECTION HEADER PATTERN
# ————————
# Matches common section/rule headers in technical docs
SECTION_HEADER_PATTERN = re.compile(
    r"(?:^|\n)"                      # start of string or newline
    r"(?:"
    r"#{1,4}\s+.+"                   # Markdown headings: ## Heading
    r"|(?:\d+\.)+\s+[A-Z].+"         # Numbered sections: 1. / 1.2. Title
    r"|\*{1,2}[A-Z][^\n]+\*{1,2}"    # Bold headings: **Title** or *Title*
    r"|SECTION\s*:\s*[^\n]+"         # SECTION: ANY TITLE
    r"|[A-Z][A-Z\s]{4,}(?=\n)"       # ALL CAPS line
    r")",
    re.MULTILINE,
)

# ————————
# SECTION SPLITTING
# ————————
def split_into_sections(text: str) -> list[dict]:
    """
    Splits text into logical sections based on detected headers.
    Returns a list of dicts: {"header": str, "body": str}

    Falls back to the entire text as one section if no headers are found.
    """
    matches = list(SECTION_HEADER_PATTERN.finditer(text))
    if not matches:
        return [{"header": "", "body": text.strip()}]

    sections = []

    for i, match in enumerate(matches):
        header_start = match.start()
        header_end = match.end()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        header = text[header_start:header_end].strip()
        body = text[header_end:section_end].strip()

        # Strip --- dividers
        body = re.sub(r"^\s*-{3,}\s*$", "", body, flags=re.MULTILINE).strip()

        if body:
            sections.append({"header": header, "body": body})

    # Preamble before first header
    first_match_start = matches[0].start()
    if first_match_start > 0:
        preamble = text[:first_match_start].strip()
        if preamble:
            sections.insert(0, {"header": "", "body": preamble})

    return sections


# ————————
# SECTION CHUNKING
# ————————
def chunk_section(header: str, body: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Chunks a single section’s body using a recursive separator strategy:
    paragraph -> sentence -> word -> character

    Each chunk is prefixed with the section header (if any).
    """

    separators = ["\n\n", "\n", ". ", " ", ""]

    def _split(text: str, seps: list[str]) -> list[str]:
        if not text:
            return []

        sep = seps[0]
        remaining_seps = seps[1:]

        # Base case: character-level split
        if not sep:
            return [
                text[i: i + chunk_size]
                for i in range(0, len(text), max(1, chunk_size - overlap))
            ]

        parts = text.split(sep)
        chunks: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + sep + part) if current else part

            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())

                # part too large — recurse
                if len(part) > chunk_size and remaining_seps:
                    chunks.extend(_split(part, remaining_seps))
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current.strip())

        return [c for c in chunks if c]

    raw_chunks = _split(body, separators)

    # Add overlap
    overlapped: list[str] = []
    for i, chunk in enumerate(raw_chunks):
        if i + 1 < len(raw_chunks) and overlap > 0:
            tail = raw_chunks[i + 1][:overlap]
            overlapped.append(chunk + " " + tail)
        else:
            overlapped.append(chunk)

    prefix = f"{header}\n\n" if header else ""
    return [prefix + c for c in overlapped]


# ————————
# FULL PIPELINE
# ————————
def chunk_text_section_aware(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Full chunking pipeline:
    1. Split document into logical sections via headers.
    2. Chunk each section independently.
    3. Return a flat list of all chunks (each with its section header).
    """
    sections = split_into_sections(text)
    all_chunks: list[str] = []

    for section in sections:
        chunks = chunk_section(section["header"], section["body"], chunk_size, overlap)
        all_chunks.extend(chunks)

    return all_chunks
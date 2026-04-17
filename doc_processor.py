from docx import Document


def _style_name(para):
    try:
        return (para.style.name or "").strip()
    except Exception:
        return ""


def extract_doc_structure(docx_path):
    doc = Document(docx_path)
    structure = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        heading_level = None
        sname = _style_name(para)
        lname = sname.lower()

        # Primary: explicit Heading styles (Heading 1, Heading 2, ...)
        if 'heading' in lname:
            # try to parse numeric level from style name
            parts = sname.split()
            try:
                # common: 'Heading 1'
                heading_level = int(parts[-1])
            except Exception:
                heading_level = 1

        # Common alternate style names that usually indicate headings
        elif any(k in lname for k in ('title', 'subtitle', 'caption')):
            if 'subtitle' in lname:
                heading_level = 2
            else:
                heading_level = 1

        else:
            # Fallback heuristic: short, predominantly bold paragraph likely a heading
            try:
                runs = list(para.runs)
                bold_runs = sum(1 for r in runs if getattr(r, 'bold', False))
                # require at least half of runs bold and reasonably short text
                if bold_runs >= 1 and len(text) <= 60 and bold_runs >= (len(runs) // 2):
                    # further exclude obvious sentence-like paragraphs
                    if not text.endswith('.') and not text.endswith('?') and not text.endswith('!'):
                        heading_level = 1
            except Exception:
                heading_level = None

        structure.append({
            "text": text,
            "heading_level": heading_level,
            "alignment": para.alignment
        })

    # post‑filter to drop any items that look too long to be real headings
    filtered = []
    for item in structure:
        if item["heading_level"]:
            # headings are normally brief; discard anything longer than 10 words
            if len(item["text"].split()) > 10:
                item["heading_level"] = None
        filtered.append(item)
    return filtered

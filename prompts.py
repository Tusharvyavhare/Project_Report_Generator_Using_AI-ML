def build_section_prompt(project_title, heading, previous_context=None):
    section_type = heading.lower()

    if "introduction" in section_type:
        focus = "background, importance, and problem overview"
    elif "methodology" in section_type or "method" in section_type:
        focus = "step-by-step approach, tools, and workflow"
    elif "result" in section_type:
        focus = "outcomes, observations, and performance"
    elif "conclusion" in section_type:
        focus = "summary, findings, and future scope"
    else:
        focus = "clear explanation relevant to the section title"

    context_note = ""
    if previous_context:
        context_note = (
            f"\nPreviously covered briefly:\n{previous_context}\n"
            "Avoid repetition.\n"
        )

    return f"""
You are writing a high-quality, professional university-level academic project report. Treat each section as a standalone paragraph that reads clearly in a professional technical document.

Project Title:
{project_title}

Section Title:
{heading}

Key aim:
Write in a precise, polished, and formal style. Use strong technical vocabulary, logical flow, and sound academic structure.

Focus specifically on:
{focus}
{context_note}

Guidelines:
- Aim for about 80–110 words delivered as one dense, coherent paragraph
- No bullets or subheadings; keep narrative format
- Avoid generic phrases like "in this project"; use concrete terms and specific outcomes
- Maintain a formal tone and accurate terminology
- Include measurable or evaluative language where appropriate (e.g., "resulted in", "achieved", "demonstrated")
- Keep grammar and punctuation professional and polished
"""

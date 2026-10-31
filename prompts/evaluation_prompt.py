EVALUATION_PROMPT = """
You are a research quality evaluator.

Determine whether the current research contains enough reliable
information to generate a useful final report.

Topic:
{query}

Research Type:
{research_type}

Research Plan:
{research_plan}

Current Analysis:
{analysis}

Research Sources:
{sources}

Research Iteration:
{iteration}

Evaluate:

1. Are the major research questions answered?
2. Are important focus areas covered?
3. Is the information sufficiently detailed?
4. Are there important unanswered questions?
5. Are enough useful sources available?

Important:

Do NOT decide based only on the number of sources.

Return ONLY valid JSON.

{{
    "enough_information": true,
    "reason": "Short explanation.",
    "missing_information": [
        "Missing information if any"
    ]
}}
"""
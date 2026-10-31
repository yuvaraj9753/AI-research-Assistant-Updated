from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem
)


def create_research_pdf(
    query: str,
    research: dict,
    final: dict
):
    """
    Generate a PDF research report.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    story = []

    story.append(
        Paragraph(
            "AI Research Assistant",
            title_style
        )
    )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            f"<b>Research Topic:</b> {query}",
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            "<b>Research Summary</b>",
            styles["Heading2"]
        )
    )

    story.append(
        Paragraph(
            research.get("summary", ""),
            styles["BodyText"]
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Insights</b>",
            styles["Heading2"]
        )
    )

    insights = research.get("insights", [])

    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        str(item),
                        styles["BodyText"]
                    )
                )
                for item in insights
            ],
            bulletType="bullet"
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Introduction</b>",
            styles["Heading2"]
        )
    )

    story.append(
        Paragraph(
            final.get("introduction", ""),
            styles["BodyText"]
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Key Points</b>",
            styles["Heading2"]
        )
    )

    key_points = final.get(
        "key_points",
        []
    )

    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        str(item),
                        styles["BodyText"]
                    )
                )
                for item in key_points
            ],
            bulletType="bullet"
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Conclusion</b>",
            styles["Heading2"]
        )
    )

    story.append(
        Paragraph(
            final.get("conclusion", ""),
            styles["BodyText"]
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Related Topics</b>",
            styles["Heading2"]
        )
    )

    related_topics = final.get(
        "related_topics",
        []
    )

    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        str(item),
                        styles["BodyText"]
                    )
                )
                for item in related_topics
            ],
            bulletType="bullet"
        )
    )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Sources</b>",
            styles["Heading2"]
        )
    )

    citations = final.get(
        "citations",
        []
    )

    story.append(
        ListFlowable(
            [
                ListItem(
                    Paragraph(
                        str(url),
                        styles["BodyText"]
                    )
                )
                for url in citations
            ],
            bulletType="bullet"
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer
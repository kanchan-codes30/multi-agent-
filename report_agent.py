"""Generates a structured research report from source material."""
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class ReportAgent(BaseAgent):

    def __init__(self):
        super().__init__("Report Generation Agent")

    def run(
        self,
        topic,
        summarized_sources,
        comparison_result,
        citations
    ):

        if not summarized_sources:
            raise ValueError(
                "Cannot generate a report without usable sources."
            )

        self.log(
            f"Generating report from "
            f"{len(summarized_sources)} sources"
        )

        date_str = datetime.now(
            timezone.utc
        ).strftime("%B %d, %Y")

        title = f"Research Report: {topic}"

        introduction = (
            f"This report summarizes information retrieved "
            f"for '{topic}' on {date_str}. It uses "
            f"{len(summarized_sources)} source(s) listed "
            "in the references. The findings are summaries "
            "of retrieved material and are not independently "
            "verified conclusions."
        )

        findings = []

        for index, source in enumerate(
            summarized_sources,
            start=1
        ):

            finding = (
                f"### {index}. "
                f"{source.get('title', 'Untitled source')}\n\n"
                f"{source.get('summary', 'No summary available.')}\n\n"
                f"**Source type:** "
                f"{source.get('source_type', 'unspecified')}\n\n"
                f"**Source URL:** "
                f"{source.get('url', 'Unavailable')}\n"
            )

            findings.append(finding)

        comparison = comparison_result or {}

        analysis = comparison.get(
            "comparison_text",
            "Comparison was not available."
        )

        similarities = comparison.get(
            "similarities",
            "Not available."
        )

        differences = comparison.get(
            "differences",
            "Not available."
        )

        conclusion = (
            f"The retrieved material provides "
            f"{len(summarized_sources)} source-based "
            f"perspective(s) on '{topic}'. "
            "No claim of factual consensus or accuracy "
            "is made by textual similarity alone. "
            "For academic or important decisions, open "
            "the cited sources and verify the original "
            "claims and publication details."
        )

        reference_text = (
            "\n".join(citations)
            if citations
            else "No reference metadata was returned."
        )

        content = f"""# {title}

*Generated on {date_str} by Multi-Agent AI Research Assistant*

## 1. Introduction

{introduction}

## 2. Research Scope and Method

The system searched Wikipedia, arXiv and Crossref.
Only results containing a usable source URL and
substantive source text were retained.

Source availability varies by topic. Crossref results
without abstracts are not treated as evidence in the
research findings.

## 3. Key Findings

{chr(10).join(findings)}

## 4. Comparative Analysis

{analysis}

**Textual Similarity:**

{similarities}

**Source Contributions:**

{differences}

## 5. Conclusion and Limitations

{conclusion}

**Limitations:**

- Automated retrieval may miss relevant publications.
- Abstracts are not full research papers.
- Source metadata may be incomplete.
- Textual similarity does not prove factual accuracy.
- The system does not independently fact-check claims.

## 6. References

{reference_text}
"""

        self.log("Report generation complete")

        return {
            "title": title,
            "content": content
        }
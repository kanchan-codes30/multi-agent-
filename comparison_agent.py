"""Compares textual coverage, not factual accuracy."""
import re

from agents.base_agent import BaseAgent

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

except Exception:
    TfidfVectorizer = None
    cosine_similarity = None


class ComparisonAgent(BaseAgent):

    def __init__(self):
        super().__init__("Comparison & Analysis Agent")

    @staticmethod
    def _tokens(text):
        return set(
            re.findall(
                r"[a-z0-9]{3,}",
                (text or "").lower()
            )
        )

    def run(self, summarized_sources):

        count = len(summarized_sources)

        self.log(
            f"Comparing {count} summarized source(s)"
        )

        if count == 0:
            raise ValueError(
                "No summarized sources available for comparison."
            )

        if count == 1:
            return {
                "comparison_text": (
                    "Only one usable source was retrieved. "
                    "A cross-source comparison is not possible. "
                    "Verify the findings using additional "
                    "independent research."
                ),
                "similarities": "Not calculated (one source).",
                "differences": "Not calculated (one source).",
                "avg_similarity": None,
                "confidence": "Not assessed"
            }

        texts = [
            source.get("summary", "")
            for source in summarized_sources
        ]

        scores = []

        # First choice: TF-IDF cosine similarity.
        if (
            TfidfVectorizer is not None
            and len([text for text in texts if text.strip()]) >= 2
        ):

            try:
                matrix = TfidfVectorizer(
                    stop_words="english"
                ).fit_transform(texts)

                similarity_matrix = cosine_similarity(matrix)

                scores = [
                    float(similarity_matrix[i][j])
                    for i in range(count)
                    for j in range(i + 1, count)
                ]

            except ValueError:
                scores = []

        # Fallback: Jaccard similarity using word overlap.
        if not scores:

            token_sets = [
                self._tokens(text)
                for text in texts
            ]

            scores = [
                len(token_sets[i] & token_sets[j])
                / max(
                    len(token_sets[i] | token_sets[j]),
                    1
                )
                for i in range(count)
                for j in range(i + 1, count)
            ]

        average = (
            sum(scores) / len(scores)
            if scores else 0.0
        )

        similarities = (
            f"Average textual similarity: {average:.2f} "
            "on a 0–1 scale. This measures shared wording "
            "and themes only. It does not establish that "
            "claims are true or independently verified."
        )

        contributions = []

        for source in summarized_sources:

            contributions.append(
                f"- {source.get('title', 'Untitled')}: "
                f"{source.get('summary', '')[:260]}"
            )

        differences = "\n".join(contributions)

        comparison_text = (
            f"Textual comparison was performed across "
            f"{count} sources. {similarities} "
            "The summaries below show each source's "
            "contribution. Differences in wording or scope "
            "should not automatically be interpreted "
            "as factual contradictions."
        )

        self.log(
            f"Comparison complete; average text similarity "
            f"{average:.2f}"
        )

        return {
            "comparison_text": comparison_text,
            "similarities": similarities,
            "differences": differences,
            "avg_similarity": round(average, 3),
            "confidence": (
                "Not assessed "
                "(similarity is not fact-checking)"
            )
        }
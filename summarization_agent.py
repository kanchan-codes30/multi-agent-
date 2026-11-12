"""Fast local extractive summarization."""
import re
from collections import Counter

from agents.base_agent import BaseAgent


STOPWORDS = set("""
a an the is are was were be been being of to in on for with
by from as at and or but if this that these those it its into
about over under than then also can could may might will would
should has have had do does did not no we they you he she their
our your
""".split())


class SummarizationAgent(BaseAgent):

    def __init__(self):
        super().__init__("Summarization Agent")

    def _summarize_text(self, text, max_sentences=5):

        text = re.sub(
            r"\s+",
            " ",
            (text or "")
        ).strip()

        if not text:
            return "No source text was provided."

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        sentences = [
            sentence.strip()
            for sentence in sentences
            if len(sentence.split()) >= 8
        ]

        if len(sentences) <= max_sentences:
            return " ".join(sentences) or text[:900]

        words = [
            word
            for word in re.findall(
                r"[a-zA-Z][a-zA-Z'-]+",
                text.lower()
            )
            if word not in STOPWORDS and len(word) > 2
        ]

        frequencies = Counter(words)

        maximum = max(
            frequencies.values(),
            default=1
        )

        frequencies = {
            word: count / maximum
            for word, count in frequencies.items()
        }

        scored_sentences = []

        for index, sentence in enumerate(sentences):

            tokens = [
                word
                for word in re.findall(
                    r"[a-zA-Z][a-zA-Z'-]+",
                    sentence.lower()
                )
                if word not in STOPWORDS
            ]

            score = sum(
                frequencies.get(word, 0)
                for word in tokens
            ) / max(len(tokens) ** 0.55, 1)

            # Give a small preference to the opening sentence.
            if index == 0:
                score *= 1.08

            scored_sentences.append(
                (score, index, sentence)
            )

        selected = sorted(
            sorted(
                scored_sentences,
                reverse=True
            )[:max_sentences],
            key=lambda item: item[1]
        )

        return " ".join(
            item[2]
            for item in selected
        )

    def run(self, sources):

        if not sources:
            raise ValueError(
                "No sources available for summarization."
            )

        self.log(
            f"Summarizing {len(sources)} source(s) "
            "using local sentence ranking"
        )

        summarized_sources = []

        for source in sources:

            item = dict(source)

            item["summary"] = self._summarize_text(
                source.get("content", "")
            )

            summarized_sources.append(item)

        self.log("Summarization complete")

        return summarized_sources
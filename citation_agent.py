"""Creates references using available source metadata."""
from agents.base_agent import BaseAgent


class CitationAgent(BaseAgent):

    def __init__(self):
        super().__init__("Citation Management Agent")

    @staticmethod
    def _author_text(authors):

        if not authors:
            return "Author unavailable"

        names = [
            str(author).strip()
            for author in authors
            if str(author).strip()
        ]

        if not names:
            return "Author unavailable"

        if len(names) > 5:
            return ", ".join(names[:5]) + ", et al."

        return ", ".join(names)

    def _format_reference(self, source, index):

        title = (
            source.get("title")
            or "Untitled source"
        )

        authors = self._author_text(
            source.get("authors", [])
        )

        year = source.get("year") or "n.d."

        url = source.get("url") or ""

        source_type = source.get(
            "source_type",
            "web"
        )

        if source_type == "arxiv":
            publisher = "arXiv"

        elif source_type == "crossref":
            publisher = "Crossref-indexed publication"

        elif source_type == "wikipedia":
            publisher = "Wikipedia"

        else:
            publisher = "Source publisher unavailable"

        doi = source.get("doi")

        link = (
            f"https://doi.org/{doi}"
            if doi
            else url
        )

        reference = (
            f"[{index}] {authors} ({year}). "
            f"{title}. {publisher}."
        )

        if link:
            reference += f" {link}"

        return reference

    def run(self, sources):

        if not sources:
            raise ValueError(
                "No sources available for citation generation."
            )

        self.log(
            f"Formatting references for {len(sources)} source(s)"
        )

        citations = [
            self._format_reference(source, index + 1)
            for index, source in enumerate(sources)
        ]

        self.log(
            "Reference generation complete. "
            "Unavailable metadata is labelled, not invented."
        )

        return citations

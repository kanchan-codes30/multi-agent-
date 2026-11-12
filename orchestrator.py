"""Coordinates all research agents and saves successful results."""

from agents.retrieval_agent import RetrievalAgent
from agents.summarization_agent import SummarizationAgent
from agents.comparison_agent import ComparisonAgent
from agents.citation_agent import CitationAgent
from agents.report_agent import ReportAgent

import database.db as db


class ResearchOrchestrator:

    def __init__(self):

        self.retrieval_agent = RetrievalAgent()
        self.summarization_agent = SummarizationAgent()
        self.comparison_agent = ComparisonAgent()
        self.citation_agent = CitationAgent()
        self.report_agent = ReportAgent()

    def run_pipeline(self, session_id, topic):

        agents = [
            self.retrieval_agent,
            self.summarization_agent,
            self.comparison_agent,
            self.citation_agent,
            self.report_agent
        ]

        all_logs = []

        # Clear logs from previous runs.
        for agent in agents:
            agent.logs.clear()

        db.update_session_status(
            session_id,
            "in_progress"
        )

        try:

            # STEP 1: Retrieve genuine research sources.
            sources = self.retrieval_agent.timed_run(topic)

            all_logs.extend(
                self.retrieval_agent.logs
            )

            if not sources:
                raise RuntimeError(
                    "No genuine research sources were retrieved."
                )

            # STEP 2: Save retrieved sources.
            for source in sources:

                source_id = db.add_source(
                    session_id,
                    source["title"],
                    source["url"],
                    source["content"],
                    source["source_type"]
                )

                source["id"] = source_id

            # STEP 3: Summarize sources.
            summarized = self.summarization_agent.timed_run(
                sources
            )

            all_logs.extend(
                self.summarization_agent.logs
            )

            for source in summarized:

                db.add_summary(
                    source["id"],
                    source["summary"]
                )

            # STEP 4: Compare summarized sources.
            comparison = self.comparison_agent.timed_run(
                summarized
            )

            all_logs.extend(
                self.comparison_agent.logs
            )

            db.add_comparison(
                session_id,
                comparison["comparison_text"],
                comparison["similarities"],
                comparison["differences"]
            )

            # STEP 5: Generate citations.
            citations = self.citation_agent.timed_run(
                sources
            )

            all_logs.extend(
                self.citation_agent.logs
            )

            # STEP 6: Generate final report.
            report = self.report_agent.timed_run(
                topic,
                summarized,
                comparison,
                citations
            )

            all_logs.extend(
                self.report_agent.logs
            )

            # STEP 7: Save report in database.
            db.add_report(
                session_id,
                report["title"],
                report["content"],
                "\n".join(citations)
            )

            # STEP 8: Mark session as completed.
            db.update_session_status(
                session_id,
                "completed"
            )

            return {
                "sources": summarized,
                "comparison": comparison,
                "citations": citations,
                "report": report,
                "logs": all_logs,
                "error": None
            }

        except Exception as exc:

            # Collect logs from all agents.
            for agent in agents:

                for line in agent.logs:

                    if line not in all_logs:
                        all_logs.append(line)

            # Mark this research session as failed.
            db.update_session_status(
                session_id,
                "failed"
            )

            print(
                "Research pipeline error:",
                str(exc)
            )

            return {
                "sources": [],
                "comparison": None,
                "citations": [],
                "report": None,
                "logs": all_logs,
                "error": str(exc)
            }
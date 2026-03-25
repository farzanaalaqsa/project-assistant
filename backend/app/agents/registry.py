from __future__ import annotations

from backend.app.agents.data_analysis import DataAnalysisAgent
from backend.app.agents.doc_qa import DocumentQAAgent


doc_qa_agent = DocumentQAAgent()
data_analysis_agent = DataAnalysisAgent()

AGENTS = {
    doc_qa_agent.name: doc_qa_agent,
    data_analysis_agent.name: data_analysis_agent,
}


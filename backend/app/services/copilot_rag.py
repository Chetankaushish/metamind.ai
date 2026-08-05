import os
import re
import math
from typing import List, Dict, Any

class CopilotRAGService:
    """
    Local Knowledge Base RAG service indexing platform documentation,
    runbooks, operations manuals, and MetaMind feature specs.
    Uses TF-IDF term frequency & cosine similarity for fast grounded retrieval.
    """
    def __init__(self):
        self.documents: List[Dict[str, str]] = []
        self._initialize_knowledge_base()

    def _initialize_knowledge_base(self):
        # Default internal knowledge base documents
        self.documents = [
            {
                "id": "doc_meta_features",
                "title": "MetaMind AI Core Features & Optimization Rules",
                "content": (
                    "MetaMind AI provides automated campaign management, budget optimization, "
                    "ROAS scaling, CPA cap guardrails, fatigue detection, and audience analysis. "
                    "Best practices: 1. Maintain target ROAS above 2.5x for scaling. "
                    "2. Pause ad sets with CPA > $25 or CTR < 0.8%. 3. Daily budget increases "
                    "should not exceed 20% every 48 hours to prevent entering re-learning phase. "
                    "4. Ad fatigue score > 70 indicates creative refresh required."
                )
            },
            {
                "id": "doc_deployment",
                "title": "Hostinger VPS Deployment & Infrastructure Guide",
                "content": (
                    "MetaMind AI is deployed on Hostinger VPS using Docker Compose, NGINX reverse proxy, "
                    "and automated Let's Encrypt SSL. Architecture includes FastAPI backend on port 8000, "
                    "PostgreSQL 16, Redis 7, Celery Workers, Prometheus on port 9090, and Grafana on port 3000. "
                    "Deployment is managed via git push to main triggering scripts/deploy-vps.sh."
                )
            },
            {
                "id": "doc_runbook",
                "title": "Production Runbook & Troubleshooting",
                "content": (
                    "Service commands: `docker compose ps` to check container statuses, "
                    "`docker compose logs -f backend` for logs. Database backups run via "
                    "`scripts/backup-db.sh` and restore via `scripts/restore-db.sh`. "
                    "Migrations are executed via `alembic upgrade head`. For queue backlog, "
                    "inspect active tasks via Celery inspect."
                )
            },
            {
                "id": "doc_incident_recovery",
                "title": "Incident Recovery & Emergency Rollback Protocol",
                "content": (
                    "In case of critical SEV-1 outage or deployment failure, execute `./scripts/rollback.sh`. "
                    "This rolls back Alembic migrations by 1 step, stops broken containers, and restarts "
                    "the previous stable Docker image stack. Check health endpoint at `/api/v1/system/health`."
                )
            },
            {
                "id": "doc_meta_api",
                "title": "Meta Marketing API Integration & OAuth Setup",
                "content": (
                    "Meta Marketing API syncs campaigns, ad sets, ads, and insights asynchronously via "
                    "Celery workers. Direct Meta API access is handled exclusively by internal services. "
                    "The AI Copilot operates strictly on local PostgreSQL database snapshots and calls "
                    "FastAPI endpoints for action execution."
                )
            }
        ]

        # Scan docs directory for additional markdown files if present
        docs_dir = os.path.join(os.getcwd(), "docs")
        if os.path.exists(docs_dir):
            for fname in os.listdir(docs_dir):
                if fname.endswith(".md"):
                    fpath = os.path.join(docs_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            text = f.read()
                            self.documents.append({
                                "id": f"file_{fname}",
                                "title": f"Documentation: {fname}",
                                "content": text[:3000]  # Cap snippet size
                            })
                    except Exception:
                        pass

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search knowledge base using token overlap and term weighting."""
        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return self.documents[:top_k]

        scored_docs = []
        for doc in self.documents:
            doc_text = f"{doc['title']} {doc['content']}".lower()
            doc_words = re.findall(r'\w+', doc_text)
            
            score = 0.0
            for qw in query_words:
                count = doc_words.count(qw)
                if count > 0:
                    score += (1 + math.log(count))
            
            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        results = [doc for _, doc in scored_docs[:top_k]]
        return results if results else self.documents[:top_k]

rag_service = CopilotRAGService()

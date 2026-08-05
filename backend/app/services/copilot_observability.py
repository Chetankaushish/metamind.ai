import time
import structlog
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

class CopilotMetrics(BaseModel):
    prompt_latency_ms: float = 0.0
    token_usage_input: int = 0
    token_usage_output: int = 0
    total_tokens: int = 0
    tool_execution_time_ms: float = 0.0
    tools_called: List[str] = Field(default_factory=list)
    has_error: bool = False
    error_message: Optional[str] = None
    hallucination_detected: bool = False
    hallucination_details: Optional[str] = None

class CopilotObservabilityTracker:
    """
    Telemetry and observability tracker for Copilot prompts, tool execution times,
    token usage, error logs, and grounding validation.
    """
    def __init__(self):
        self.metrics_history: List[CopilotMetrics] = []

    def create_tracker(self) -> 'CopilotSessionTracker':
        return CopilotSessionTracker(self)

    def log_metrics(self, metrics: CopilotMetrics):
        self.metrics_history.append(metrics)
        # Keep last 500 requests in memory
        if len(self.metrics_history) > 500:
            self.metrics_history = self.metrics_history[-500:]
        
        logger.info(
            "copilot_telemetry",
            latency_ms=metrics.prompt_latency_ms,
            total_tokens=metrics.total_tokens,
            tools=metrics.tools_called,
            error=metrics.has_error,
            hallucination=metrics.hallucination_detected
        )

class CopilotSessionTracker:
    def __init__(self, parent: CopilotObservabilityTracker):
        self.parent = parent
        self.start_time = time.time()
        self.tool_start_time: float = 0.0
        self.metrics = CopilotMetrics()

    def start_tool_call(self, tool_name: str):
        self.tool_start_time = time.time()
        self.metrics.tools_called.append(tool_name)

    def end_tool_call(self):
        if self.tool_start_time > 0:
            elapsed = (time.time() - self.tool_start_time) * 1000.0
            self.metrics.tool_execution_time_ms += round(elapsed, 2)
            self.tool_start_time = 0.0

    def record_tokens(self, input_text: str, output_text: str):
        # Approximate 1 token ~ 4 characters
        self.metrics.token_usage_input = max(1, len(input_text) // 4)
        self.metrics.token_usage_output = max(1, len(output_text) // 4)
        self.metrics.total_tokens = self.metrics.token_usage_input + self.metrics.token_usage_output

    def record_error(self, err_msg: str):
        self.metrics.has_error = True
        self.metrics.error_message = err_msg

    def verify_grounding(self, response_text: str, valid_campaign_ids: List[str]):
        """Detect potential hallucinations where non-existent IDs are cited."""
        import re
        referenced_ids = re.findall(r'1202\d{10}', response_text)
        for rid in referenced_ids:
            if rid not in valid_campaign_ids:
                self.metrics.hallucination_detected = True
                self.metrics.hallucination_details = f"Referenced unknown campaign ID: {rid}"
                break

    def finalize(self) -> CopilotMetrics:
        return self.finish()

    def finish(self) -> CopilotMetrics:
        self.metrics.prompt_latency_ms = round((time.time() - self.start_time) * 1000.0, 2)
        self.parent.log_metrics(self.metrics)
        return self.metrics

copilot_observability = CopilotObservabilityTracker()

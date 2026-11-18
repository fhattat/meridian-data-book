# ch17_agent_safety/guardrails.py
import json, uuid, datetime as dt
import duckdb

POLICY = {
    "pipeline_agent": {"allowed": {"profile", "ingest", "clean", "quality", "modeling",
                                    "incident", "catalog", "review"},
                       "max_steps": 30, "max_tokens": 200_000},
    "support_assistant": {"allowed": {"search_docs"}, "max_steps": 6, "max_tokens": 20_000},
}
# (tool, action) -> needs human approval
REQUIRE_APPROVAL = {("ingest", "full_reload"), ("ingest", "backfill_long"),
                    ("clean", "rebuild"), ("quality", "release_quarantine"),
                    ("incident", "close_incident"), ("incident", "send_email"),
                    ("catalog", "approve_description"), ("review", "drop_table")}

class GuardrailError(Exception):
    pass

class Guard:
    def __init__(self, agent: str, tools: dict, db="data/meridian.duckdb"):
        self.agent, self.tools, self.policy = agent, tools, POLICY[agent]
        self.run_id, self.steps, self.tokens = uuid.uuid4().hex[:12], 0, 0
        self.history = []          # (tool, args) pairs; used to catch a repeating loop
        self.con = duckdb.connect(db)

    def _audit(self, tool, args, status, approved_by=None):
        self.con.execute("INSERT INTO quality.agent_audit VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [self.run_id, self.agent, tool, json.dumps(args, default=str),
                          status, approved_by, dt.datetime.now(dt.timezone.utc)])

    def call(self, tool: str, args: dict, action: str = "run", tokens: int = 0,
             approver=None):
        self.steps += 1
        self.tokens += tokens
        if tool not in self.policy["allowed"]:
            self._audit(tool, args, "blocked_not_allowed")
            raise GuardrailError(f"{tool} is not allowed for this agent")
        if self.steps > self.policy["max_steps"] or self.tokens > self.policy["max_tokens"]:
            self._audit(tool, args, "blocked_budget")
            raise GuardrailError("step or token budget exceeded")
        signature = (tool, json.dumps(args, sort_keys=True, default=str))
        self.history.append(signature)
        if self.history.count(signature) >= 3:
            self._audit(tool, args, "blocked_loop")
            raise GuardrailError("same call for the third time; possible loop")
        approved_by = None
        if (tool, action) in REQUIRE_APPROVAL:
            try:
                approved_by = require_approval(tool, action, args, approver)
            except GuardrailError:
                self._audit(tool, args, "rejected")
                raise
        result = self.tools[tool](**args)
        self._audit(tool, args, "ok", approved_by)
        return result

def require_approval(tool, action, args, approver):
    """Stops if there is no human approval. approver: the function that asks for it (CLI, Slack, email...)."""
    if approver is None:
        raise GuardrailError(f"{tool}.{action} requires human approval")
    who = approver(f"Run {tool}.{action}? {json.dumps(args, default=str)}")
    if not who:
        raise GuardrailError(f"{tool}.{action} was rejected")
    return who

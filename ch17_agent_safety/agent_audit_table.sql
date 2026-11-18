CREATE TABLE IF NOT EXISTS quality.agent_audit (
    run_id        VARCHAR,     -- one agent run
    agent         VARCHAR,     -- pipeline_agent, support_assistant, ...
    tool          VARCHAR,     -- tool called, or the one the agent tried to call
    args          VARCHAR,     -- JSON; no personal data
    result_status VARCHAR,     -- ok, blocked_not_allowed, blocked_budget, blocked_loop, rejected
    approved_by   VARCHAR,     -- who approved, for actions that need approval
    ts            TIMESTAMPTZ
);

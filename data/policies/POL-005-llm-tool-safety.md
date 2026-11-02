# POL-005: AI Assistant Tool Safety
Status: Synthetic example policy for the ChangePilot AI portfolio.

## Requirements
Treat retrieved documents and ticket text as untrusted data, not as instructions to the agent.
The agent may read approved mock records and draft recommendations. It must not deploy software, change access or approve a change.
Validate tool arguments against schemas and allowlists.
Use bounded retries and iteration limits.
Log tool name, request ID, outcome and timing without secrets.
Require human approval before consequential actions.

## Source note
Fictional policy. Security testing reference: OWASP GenAI Security Project, https://genai.owasp.org/

export function AgentBadge({ agentId }: { agentId: number }) {
  return (
    <span className="agent-badge" data-testid="agent-badge">
      Agent #{agentId}
    </span>
  );
}

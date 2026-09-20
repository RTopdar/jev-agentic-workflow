export function EscalationBanner({ status }: { status: string }) {
  if (status !== "escalated") return null;
  return (
    <div role="alert" className="escalation-banner">
      This conversation has been moved to a human agent who will take care of it.
    </div>
  );
}

export default function PlaygroundPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Coral Playground</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Interactive SQL REPL — run ad-hoc Coral queries against live sources.
        </p>
      </header>

      <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-raise)] p-12 flex flex-col items-center justify-center text-center">
        <p className="text-sm font-semibold text-[var(--color-text-primary)] mb-2">
          Coral SQL REPL
        </p>
        <p className="text-xs text-[var(--color-text-muted)] max-w-sm">
          Interactive query editor coming soon. To run SQL now, use the CLI:
        </p>
        <code className="mt-3 font-mono text-xs bg-[var(--color-border)] px-3 py-2 rounded text-[var(--color-text-primary)]">
          kraken voyage:compile exec_escalation --params &apos;{"{}"}&apos;
        </code>
      </div>
    </div>
  );
}

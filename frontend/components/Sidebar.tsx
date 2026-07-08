export function Sidebar({ live, tenantCount }: { live: boolean; tenantCount: number }) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__mark">◆</span> Foresight
      </div>

      <div className="nav__section">Monitoring</div>
      <div className="nav__item nav__item--active">
        <span className="nav__ico">◎</span> Anomalies
      </div>
      <div className="nav__item nav__item--muted">
        <span className="nav__ico">📈</span> Metrics
      </div>
      <div className="nav__item nav__item--muted">
        <span className="nav__ico">🔔</span> Alerts
      </div>

      <div className="nav__section">Workspace</div>
      <div className="nav__item nav__item--muted">
        <span className="nav__ico">🏢</span> Accounts <span style={{ marginLeft: "auto", color: "var(--faint)" }}>{tenantCount}</span>
      </div>
      <div className="nav__item nav__item--muted">
        <span className="nav__ico">⚙️</span> Settings
      </div>

      <div className="sidebar__spacer" />
      <div className="sidebar__foot">
        <span className="livepill">
          <span className={`livedot ${live ? "" : "livedot--off"}`} />
          {live ? "Live · API connected" : "Static snapshot"}
        </span>
      </div>
    </aside>
  );
}

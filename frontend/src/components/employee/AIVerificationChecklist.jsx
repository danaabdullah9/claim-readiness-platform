import { useEffect, useRef, useState } from "react";

const STATE_ICON = { pass: "✓", warn: "!", fail: "✕" };
const STATE_WORD = { pass: "Verified", warn: "Needs attention", fail: "Failed" };

// سرعة مرور المؤشر على البنود (بالمللي ثانية)
const STEP_MS = 260;

function Ring({ counts }) {
  const total = counts.total || 1;
  const passPct = (counts.pass / total) * 100;
  const warnPct = (counts.warn / total) * 100;
  const failPct = (counts.fail / total) * 100;

  return (
    <div
      className="vc-ring"
      style={{
        "--pass": `${passPct}%`,
        "--warn": `${passPct + warnPct}%`,
        "--fail": `${passPct + warnPct + failPct}%`,
      }}
    >
      <div className="vc-ring-core">
        <strong>{counts.pass}</strong>
        <small>of {counts.total}</small>
      </div>
    </div>
  );
}

function AIVerificationChecklist({ checklist }) {
  const items = checklist?.items || [];
  const groups = checklist?.groups || [];
  const counts = checklist?.counts || { pass: 0, warn: 0, fail: 0, total: 0 };

  const [revealed, setRevealed] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const [scanning, setScanning] = useState(true);
  // القائمة طويلة (30+ فحصًا)، فتُطوى افتراضيًا بعد انتهاء الفحص
  const [showAll, setShowAll] = useState(true);
  const [openGroups, setOpenGroups] = useState({});
  const timers = useRef([]);

  // المرور على البنود واحدًا واحدًا كما لو أن المدقق يفحصها أمامك
  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setRevealed(0);
    setScanning(true);

    if (items.length === 0) {
      setScanning(false);
      return undefined;
    }

    items.forEach((_, index) => {
      timers.current.push(
        setTimeout(() => {
          setRevealed(index + 1);
          if (index === items.length - 1) {
            setScanning(false);
            setShowAll(false);
          }
        }, STEP_MS * (index + 1)),
      );
    });

    return () => timers.current.forEach(clearTimeout);
  }, [checklist]);

  function skip() {
    timers.current.forEach(clearTimeout);
    setRevealed(items.length);
    setScanning(false);
  }

  function toggleGroup(name) {
    setOpenGroups((current) => ({ ...current, [name]: !current[name] }));
  }

  if (!checklist) {
    return (
      <section className="employee-review-card vc-card">
        <p className="vc-empty">Verification results are not available for this claim.</p>
      </section>
    );
  }

  const failures = items.filter((item) => item.state === "fail").slice(0, revealed);
  const warnings = items.filter((item) => item.state === "warn").slice(0, revealed);

  let cursor = 0;

  return (
    <section className={`employee-review-card vc-card vc-${checklist.verdict}`} aria-labelledby="vc-title">
      <div className="vc-head">
        <div>
          <span className="employee-ai-label">✦ AI-assisted</span>
          <h2 id="vc-title">Verification Checklist</h2>
          <p className="vc-sub">
            {scanning
              ? `Checking ${revealed} of ${items.length}…`
              : checklist.verdict === "pass"
              ? `All ${counts.total} checks passed. Nothing blocks this claim.`
              : checklist.verdict === "warn"
              ? `${counts.warn} check(s) need your attention before approving.`
              : `${counts.fail} check(s) failed. Resolve them before approving.`}
          </p>
        </div>
        <Ring counts={{ ...counts, pass: Math.min(counts.pass, revealed) }} />
      </div>

      <div className="vc-tally">
        <span className="vc-tally-pass">{Math.min(counts.pass, revealed)} passed</span>
        <span className="vc-tally-warn">{warnings.length} warnings</span>
        <span className="vc-tally-fail">{failures.length} failed</span>
        {scanning ? (
          <button type="button" className="vc-skip" onClick={skip}>
            Skip animation
          </button>
        ) : (
          <button type="button" className="vc-skip" onClick={() => setShowAll((value) => !value)}>
            {showAll ? `Hide all ${items.length} checks` : `Show all ${items.length} checks`}
          </button>
        )}
      </div>

      {groups.map((group) => {
        const counts = group.items.reduce(
          (totals, entry) => ({ ...totals, [entry.state]: (totals[entry.state] || 0) + 1 }),
          {},
        );
        const groupState = counts.fail ? "fail" : counts.warn ? "warn" : "pass";
        const isOpen = showAll || openGroups[group.name];

        return (
        <div className={`vc-group vc-group-${groupState}`} key={group.name}>
          <button type="button" className="vc-group-head" onClick={() => toggleGroup(group.name)} aria-expanded={isOpen}>
            <span className={`vc-group-dot vc-dot-${groupState}`} aria-hidden="true" />
            <span className="vc-group-title">
              <h3>{group.name}</h3>
              <small>{group.caption}</small>
            </span>
            <span className="vc-group-count">
              {counts.pass || 0}/{group.items.length}
            </span>
            <span className="vc-chevron" aria-hidden="true">⌄</span>
          </button>

          <ul className={`vc-list${isOpen ? "" : " is-collapsed"}`}>
            {group.items.map((item) => {
              const index = cursor++;
              const isVisible = index < revealed;
              const isActive = index === revealed - 1 && scanning;
              const isOpen = expanded === item.id;

              return (
                <li
                  key={item.id}
                  className={`vc-item vc-${item.state}${isVisible ? " is-visible" : ""}${isActive ? " is-active" : ""}${isOpen ? " is-open" : ""}`}
                >
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => setExpanded(isOpen ? null : item.id)}
                  >
                    <span className="vc-icon" aria-hidden="true">
                      {isVisible ? STATE_ICON[item.state] : ""}
                    </span>
                    <span className="vc-copy">
                      <strong>{item.label}</strong>
                      {isVisible && item.evidence && <em>{item.evidence}</em>}
                    </span>
                    <span className="vc-state">{isVisible ? STATE_WORD[item.state] : "…"}</span>
                    <span className="vc-chevron" aria-hidden="true">⌄</span>
                  </button>

                  {isOpen && isVisible && (
                    <div className="vc-detail">
                      <p>{item.detail}</p>
                      {item.action && (
                        <p className="vc-action">
                          <strong>What to do:</strong> {item.action}
                        </p>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
        );
      })}

      {checklist.policy_reference && (
        <p className="vc-source">
          Benefit and compliance checks are evaluated against the{" "}
          <strong>{checklist.policy_reference.name}</strong> — {checklist.policy_reference.edition}.
        </p>
      )}

      {!scanning && (failures.length > 0 || warnings.length > 0) && (
        <div className={`vc-summary vc-summary-${failures.length ? "fail" : "warn"}`} role="alert">
          <strong>
            {failures.length
              ? `${failures.length} blocking issue${failures.length > 1 ? "s" : ""}`
              : `${warnings.length} item${warnings.length > 1 ? "s" : ""} to review`}
          </strong>
          <ul>
            {[...failures, ...warnings].map((item) => (
              <li key={item.id}>
                <span className={`vc-pill vc-pill-${item.state}`}>{item.group}</span>
                <div>
                  <strong>{item.label}</strong>
                  <p>{item.detail}</p>
                  {item.action && <p className="vc-action">{item.action}</p>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export default AIVerificationChecklist;
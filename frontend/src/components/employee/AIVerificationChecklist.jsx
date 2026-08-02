import { useState } from "react";

const stateIcons = { success: "✓", warning: "!", error: "×" };

function getExplanation(item) {
  if (item.detail) return item.detail;
  if (item.state === "success") return "This check passed based on the information detected in the uploaded documents.";
  if (item.state === "warning") return "This finding may need employee review before the claim can move forward.";
  return "This requirement was not confirmed in the uploaded claim documents.";
}

function AIVerificationChecklist({ items }) {
  const [expandedItem, setExpandedItem] = useState(null);

  return (
    <section className="employee-review-card" aria-labelledby="verification-title">
      <div className="employee-section-heading"><div><span className="employee-ai-label">✦ AI-assisted</span><h2 id="verification-title">AI Verification Checklist</h2></div></div>
      <ul className="employee-checklist">{items.map((item) => {
        const isExpanded = expandedItem === item.label;
        return (
          <li key={item.label} className={`employee-check-${item.state}${isExpanded ? " is-expanded" : ""}`}>
            <button type="button" aria-expanded={isExpanded} onClick={() => setExpandedItem(isExpanded ? null : item.label)}>
              <span className="employee-check-icon" aria-hidden="true">{stateIcons[item.state]}</span>
              <span className="employee-check-copy"><strong>{item.label}</strong><small>{isExpanded ? getExplanation(item) : "View finding"}</small></span>
              <span className="employee-check-state">{item.state}</span>
              <span className="employee-check-chevron" aria-hidden="true">⌄</span>
            </button>
          </li>
        );
      })}</ul>
    </section>
  );
}

export default AIVerificationChecklist;

function AIClaimSummary({ summary, highlights, confidence }) {
  return (
    <section className="employee-review-card employee-ai-card" aria-labelledby="ai-summary-title">
      <div className="employee-section-heading"><div><span className="employee-ai-label">✦ AI-generated</span><h2 id="ai-summary-title">AI Claim Summary</h2></div><span className="employee-confidence">{confidence}% confidence</span></div>
      <p className="employee-ai-summary">{summary}</p>
      <p className="employee-ai-disclaimer">AI insights support review only. They do not approve or reject this claim.</p>
      <div className="employee-subsection-heading"><h3>AI Highlights</h3></div>
      <dl className="employee-highlight-grid">{Object.entries(highlights).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    </section>
  );
}

export default AIClaimSummary;

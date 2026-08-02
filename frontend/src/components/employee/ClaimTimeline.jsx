import { timelineStages } from "../../data/employeeClaims";

function ClaimTimeline({ currentStage }) {
  const currentIndex = timelineStages.indexOf(currentStage);
  return (
    <section className="employee-review-card" aria-labelledby="timeline-title">
      <div className="employee-section-heading"><div><p className="employee-eyebrow">Workflow</p><h2 id="timeline-title">Claim Timeline</h2></div></div>
      <ol className="employee-timeline">{timelineStages.map((stage, index) => <li key={stage} className={index < currentIndex ? "is-complete" : index === currentIndex ? "is-current" : ""}><span aria-hidden="true">{index < currentIndex ? "✓" : index + 1}</span><div><strong>{stage}</strong>{index === currentIndex && <small>Current stage</small>}</div></li>)}</ol>
    </section>
  );
}

export default ClaimTimeline;

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { customerActivity, customerClaims, customerDraft, customerMessages } from "../data/customerDashboardData";
import "./CustomerDashboard.css";

const FILTERS = ["All", "Active", "Completed"];
const ACTIVE = new Set(["Draft", "Submitted", "Under Review", "Action Required"]);
const COMPLETE = new Set(["Approved", "Rejected", "Paid"]);
const STAGES = ["Submitted", "AI Review", "Human Review", "Decision"];

function Icon({ type }) {
  const paths = { bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>, arrow: <path d="m9 18 6-6-6-6"/>, search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>, close: <><path d="m6 6 12 12"/><path d="M18 6 6 18"/></> };
  return <svg className="cd-icon" viewBox="0 0 24 24" aria-hidden="true">{paths[type]}</svg>;
}
function Status({ value }) { return <span className={`cd-status status-${value.toLowerCase().replaceAll(" ", "-")}`}>{value}</span>; }

function StageIndicator({ claim }) {
  if (!ACTIVE.has(claim.status) || claim.status === "Draft") return null;
  const current = claim.stage ?? (claim.status === "Action Required" ? 2 : 1);
  return <ol className="cd-stages" aria-label="Claim processing stages">{STAGES.map((stage, index) => <li className={index < current ? "done" : index === current ? "current" : ""} aria-current={index === current ? "step" : undefined} key={stage}><i/><span>{stage}</span></li>)}</ol>;
}

function NotificationPopover({ messages, onOpen, onMarkAllRead, onClose }) {
  const popoverRef = useRef(null);
  useEffect(() => {
    popoverRef.current?.focus();
    function clickAway(event) { if (!popoverRef.current?.contains(event.target) && !event.target.closest(".cd-bell")) onClose(); }
    function escape(event) { if (event.key === "Escape") onClose(); }
    document.addEventListener("mousedown", clickAway); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", clickAway); document.removeEventListener("keydown", escape); };
  }, [onClose]);
  return <section className="cd-notifications" ref={popoverRef} tabIndex="-1" aria-label="Notifications"><div className="cd-notification-head"><div><strong>Notifications</strong><span>Claim updates and requests</span></div><button onClick={onClose} aria-label="Close notifications"><Icon type="close"/></button></div><div className="cd-notification-list">{messages.length ? messages.map((message) => <button className={`cd-notification ${message.unread ? "unread" : ""}`} onClick={() => onOpen(message.claimId)} key={message.id}><span className={`cd-notification-type type-${message.type.toLowerCase().replaceAll(" ", "-")}`}>{message.type}</span><strong>{message.title}</strong><p>{message.preview}</p><small><span>{message.claimId}</span><time>{message.timestamp}</time></small></button>) : <div className="cd-notification-empty"><strong>No new notifications</strong><p>You’re all caught up.</p></div>}</div>{messages.some((message) => message.unread) && <button className="cd-mark-read" onClick={onMarkAllRead}>Mark all as read</button>}</section>;
}

function ClaimDetails({ claim, messages, onClose, onRespond }) {
  const [reply, setReply] = useState(""); const [thread, setThread] = useState(messages.flatMap((message) => message.thread));
  function sendReply(event) { event.preventDefault(); if (!reply.trim()) return; setThread((items) => [...items, { from: "customer", text: reply.trim(), time: "Just now" }]); setReply(""); }
  return <div className="cd-overlay" role="dialog" aria-modal="true" aria-labelledby="claim-detail-title"><article className="cd-detail"><button className="cd-close" onClick={onClose} aria-label="Close claim details"><Icon type="close"/></button><p className="cd-eyebrow">Claim details</p><h2 id="claim-detail-title">{claim.id}</h2><div className="cd-detail-meta"><div><span>Status</span><Status value={claim.status}/></div><div><span>Submitted</span><strong>{claim.submitted}</strong></div><div><span>Claim amount</span><strong>{claim.amount || "Not available"}</strong></div></div>{claim.request && <section className="cd-request"><h3>Employee request</h3><strong>{claim.request.title}</strong><p>{claim.request.message}</p><button className="cd-primary" onClick={onRespond}>Respond to request</button></section>}<div className="cd-detail-grid"><section><h3>Submitted documents</h3><ul className="cd-docs">{claim.documents.map((doc) => <li key={doc}>{doc}</li>)}</ul><h3>Claim activity</h3><ol className="cd-timeline">{claim.timeline.map(([date, label]) => <li key={date + label}><span>{date}</span><strong>{label}</strong></li>)}</ol></section><section><h3>Messages about this claim</h3>{thread.length ? <div className="cd-thread">{thread.map((item, index) => <div className={`cd-bubble ${item.from}`} key={index}><strong>{item.from === "employee" ? "Claims reviewer" : "You"}</strong><p>{item.text}</p><time>{item.time}</time></div>)}</div> : <p className="cd-empty-inline">No messages for this claim yet.</p>}{claim.request && <form className="cd-reply" onSubmit={sendReply}><label htmlFor="claim-reply">Your response</label><textarea id="claim-reply" value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Write a claim-related response…"/><button className="cd-primary" type="submit">Send response</button><small>Demo only — responses are not sent or saved.</small></form>}</section></div></article></div>;
}

function CustomerDashboard({ user, onStartClaim, onSignOut }) {
  const [filter, setFilter] = useState("All"); const [search, setSearch] = useState(""); const [dashboardClaims, setDashboardClaims] = useState(customerClaims); const [messages, setMessages] = useState(customerMessages); const [selectedClaim, setSelectedClaim] = useState(null); const [notificationsOpen, setNotificationsOpen] = useState(false);
  const bellRef = useRef(null);
  const closeNotifications = useCallback(() => { setNotificationsOpen(false); requestAnimationFrame(() => bellRef.current?.focus()); }, []);
  useEffect(() => {
    if (!user?.id) return undefined;
    let active = true;
    async function loadDashboard() {
      try {
        const response = await fetch(`http://127.0.0.1:8001/api/customers/${user.id}/dashboard`);
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Could not load dashboard updates.");
        if (active) {
          setDashboardClaims(result.data.claims);
          setMessages(result.data.notifications);
        }
      } catch (error) {
        console.error("Customer dashboard update failed:", error);
      }
    }
    loadDashboard();
    const timer = window.setInterval(loadDashboard, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, [user?.id]);
  const unread = messages.filter((message) => message.unread).length;
  const claims = useMemo(() => dashboardClaims.filter((claim) => { const match = filter === "All" || (filter === "Active" ? ACTIVE.has(claim.status) : COMPLETE.has(claim.status)); return match && claim.id.toLowerCase().includes(search.trim().toLowerCase()); }).sort((a, b) => Number(ACTIVE.has(b.status)) - Number(ACTIVE.has(a.status)) || (b.order ?? 0) - (a.order ?? 0)), [dashboardClaims, filter, search]);
  const openClaim = (id) => { setSelectedClaim(dashboardClaims.find((claim) => claim.id === id)); setMessages((items) => items.map((message) => message.claimId === id ? { ...message, unread: false } : message)); setNotificationsOpen(false); };
  const firstName = user?.name?.trim().split(/\s+/)[0] || "there";
  const summaries = [["Total Claims", dashboardClaims.length, "All", "All submitted and draft claims"], ["Under Review", dashboardClaims.filter((claim) => claim.status === "Under Review").length, "Active", "Claims currently being reviewed"], ["Approved", dashboardClaims.filter((claim) => claim.status === "Approved").length, "Completed", "Successfully reviewed claims"], ["Pending Action", dashboardClaims.filter((claim) => claim.status === "Action Required").length, "Active", "Claims waiting for your response"]];
  return <div className="customer-dashboard"><header className="cd-topbar"><div className="cd-brand"><span className="cd-mark">care<strong>flow</strong></span></div><div className="cd-top-actions"><div className="cd-notification-wrap"><button ref={bellRef} className="cd-bell" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`} aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen((open) => !open)}><Icon type="bell"/>{unread > 0 && <span aria-hidden="true">{unread}</span>}</button>{notificationsOpen && <NotificationPopover messages={messages} onOpen={openClaim} onMarkAllRead={() => setMessages((items) => items.map((message) => ({ ...message, unread: false })))} onClose={closeNotifications}/>}</div><button className="cd-signout" onClick={onSignOut}>Sign out</button></div></header><main className="cd-main"><section className="cd-hero"><div><p className="cd-eyebrow">Member dashboard</p><h1>Welcome back, {firstName}</h1><p>Track your reimbursement claims and stay updated on their progress.</p></div><button className="cd-primary cd-start" onClick={onStartClaim}>Start New Claim</button></section><section className="cd-summaries" aria-label="Claims summary">{summaries.map(([label, count, target, helper]) => <button className={filter === target ? "selected" : ""} key={label} onClick={() => { setFilter(target); document.getElementById("my-claims")?.scrollIntoView({ behavior: "smooth" }); }}><span>{label}</span><strong>{count}</strong><small>{helper}</small></button>)}</section><section className="cd-claims" id="my-claims"><div className="cd-claims-head"><div><p className="cd-eyebrow">Your claims</p><h2>My Claims</h2></div><label className="cd-search"><span className="visually-hidden">Search by claim reference</span><Icon type="search"/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search claim reference"/></label></div><div className="cd-filters" role="group" aria-label="Filter claims">{FILTERS.map((item) => <button className={filter === item ? "active" : ""} aria-pressed={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div><div className="cd-claim-grid">{claims.map((claim) => <article className="cd-claim-card" key={claim.id}><div className="cd-card-head"><div><span>{claim.category}</span><h3>{claim.id}</h3></div><Status value={claim.status}/></div><p>{claim.description}</p><dl><div><dt>Submitted</dt><dd>{claim.submitted}</dd></div><div><dt>Amount</dt><dd>{claim.amount || "—"}</dd></div></dl><StageIndicator claim={claim}/><div className="cd-latest"><span>Latest update</span><strong>{claim.latestUpdate}</strong></div><div className="cd-card-actions">{claim.status === "Action Required" && <button className="cd-primary" onClick={() => openClaim(claim.id)}>Respond</button>}<button className="cd-secondary" onClick={() => openClaim(claim.id)}>View Details <Icon type="arrow"/></button></div></article>)}{!claims.length && <div className="cd-empty"><h3>No matching claims</h3><p>Try another filter or search reference.</p><button className="cd-secondary" onClick={() => { setFilter("All"); setSearch(""); }}>Clear filters</button></div>}</div></section><section className="cd-activity" aria-labelledby="activity-title"><div><p className="cd-eyebrow">Latest updates</p><h2 id="activity-title">Recent Activity</h2></div><ol>{customerActivity.map((item) => <li key={item.date + item.claimId}><time>{item.date}</time><span>{item.text} <button onClick={() => openClaim(item.claimId)}>{item.claimId}</button></span></li>)}</ol></section><section className="cd-lower">{customerDraft && <article className="cd-panel cd-draft"><p className="cd-eyebrow">Frontend demo draft</p><h2>Continue Your Draft</h2><p>Last edited {customerDraft.lastEdited}</p><span>{customerDraft.stage}</span><button className="cd-secondary" onClick={onStartClaim}>Resume</button></article>}<article className="cd-panel cd-help"><p className="cd-eyebrow">Support</p><h2>Need Help?</h2><div>{["Claim Guidelines", "Accepted Documents", "Frequently Asked Questions", "Contact Support"].map((label) => <button key={label} onClick={() => alert(`${label} information will be available here.`)}>{label}<Icon type="arrow"/></button>)}</div></article></section></main>{selectedClaim && <ClaimDetails claim={selectedClaim} messages={messages.filter((message) => message.claimId === selectedClaim.id)} onClose={() => setSelectedClaim(null)} onRespond={() => document.getElementById("claim-reply")?.focus()}/>}</div>;
}
export default CustomerDashboard;

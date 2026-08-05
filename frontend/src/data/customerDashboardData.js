// Frontend demo data only. Replace this module with customer-scoped API calls when available.
export const customerClaims = [
  {
    id: "CLM-2026-1048", submitted: "30 Jul 2026", amount: "SAR 1,240.00", status: "Action Required",
    description: "We need additional information from you.", latestUpdate: "Clearer invoice requested 2 hours ago",
    category: "Medical reimbursement", stage: 2, order: 5, documents: ["Medical prescription.pdf", "Invoice scan.jpg"],
    request: { title: "Upload a clearer invoice", message: "The invoice image is blurred around the total. Please upload a clear, complete copy.", date: "2 hours ago", action: "Upload a clearer invoice" },
    timeline: [
      ["30 Jul 2026", "Documents uploaded"], ["30 Jul 2026", "Claim submitted"],
      ["31 Jul 2026", "Claim entered review"], ["Today, 10:15", "Reviewer requested a clearer invoice"],
    ],
  },
  {
    id: "CLM-2026-1032", submitted: "24 Jul 2026", amount: "SAR 680.00", status: "Under Review",
    description: "A reviewer is checking your documents.", latestUpdate: "Review started 1 Aug 2026", category: "Outpatient care", stage: 2, order: 4,
    documents: ["Clinic invoice.pdf", "Prescription.pdf"], timeline: [["24 Jul 2026", "Claim submitted"], ["1 Aug 2026", "Claim entered review"]],
  },
  {
    id: "CLM-2026-0997", submitted: "12 Jul 2026", amount: "SAR 425.50", status: "Approved",
    description: "Your claim has been approved.", latestUpdate: "Approved 18 Jul 2026", category: "Pharmacy", order: 3,
    documents: ["Pharmacy invoice.pdf", "Prescription.jpg"], timeline: [["12 Jul 2026", "Claim submitted"], ["14 Jul 2026", "Claim entered review"], ["18 Jul 2026", "Claim approved"]],
  },
  {
    id: "CLM-2026-0941", submitted: "28 Jun 2026", amount: "SAR 310.00", status: "Rejected",
    description: "Open the claim to view the decision reason.", latestUpdate: "Decision issued 3 Jul 2026", category: "Outpatient care", order: 2,
    documents: ["Invoice.pdf"], timeline: [["28 Jun 2026", "Claim submitted"], ["3 Jul 2026", "Claim rejected — required prescription was not provided"]],
  },
  {
    id: "DRAFT-204", submitted: "Not submitted", amount: null, status: "Draft",
    description: "Complete your documents when you are ready.", latestUpdate: "Last edited 4 Aug 2026", category: "Draft reimbursement", order: 1,
    documents: ["Invoice draft.pdf"], timeline: [["4 Aug 2026", "Invoice uploaded; draft remains on this device"]],
  },
];

export const customerMessages = [
  { id: 1, claimId: "CLM-2026-1048", sender: "Claims reviewer", type: "Document requested", title: "Clearer invoice required", preview: "Please upload a clear and complete copy of your invoice.", timestamp: "2 hours ago", unread: true,
    thread: [{ from: "employee", text: "Hello Ahmed, the invoice image is blurred around the total. Please upload a clear, complete copy so we can continue reviewing your claim.", time: "Today, 10:15" }] },
  { id: 2, claimId: "CLM-2026-1032", sender: "Claims reviewer", type: "Claim under review", title: "Review in progress", preview: "Your documents are now being reviewed.", timestamp: "1 Aug", unread: false,
    thread: [{ from: "employee", text: "Your documents are now being reviewed. We will contact you here if anything else is needed.", time: "1 Aug, 14:30" }, { from: "customer", text: "Thank you for the update.", time: "1 Aug, 15:05" }] },
];

export const customerActivity = [
  { date: "Today", text: "A reviewer requested a clearer invoice for", claimId: "CLM-2026-1048" },
  { date: "1 Aug", text: "Your claim entered human review:", claimId: "CLM-2026-1032" },
  { date: "18 Jul", text: "Your reimbursement claim was approved:", claimId: "CLM-2026-0997" },
];

export const customerDraft = { claimId: "DRAFT-204", lastEdited: "4 Aug 2026", stage: "Documents · 1 of 2 uploaded" };

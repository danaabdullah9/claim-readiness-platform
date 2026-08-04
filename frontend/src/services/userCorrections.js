const API_BASE_URL = "http://127.0.0.1:8001";

async function readResponse(response) {
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || "Unable to process corrections.");
  }
  return result.data;
}

export async function fetchUserCorrections(claimId) {
  const response = await fetch(`${API_BASE_URL}/api/claims/${claimId}/corrections`);
  return readResponse(response);
}

export async function submitUserCorrections(claimId, corrections) {
  const response = await fetch(`${API_BASE_URL}/api/claims/${claimId}/corrections`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ corrections }),
  });
  return readResponse(response);
}

export async function reviewUserCorrection(claimId, field, review) {
  const response = await fetch(
    `${API_BASE_URL}/api/claims/${claimId}/corrections/${encodeURIComponent(field)}/review`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(review),
    },
  );
  return readResponse(response);
}

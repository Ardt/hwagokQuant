// OCI Object Storage pre-authenticated request base URL
export const OCI_RESULTS_URL = process.env.OCI_RESULTS_URL || "";

export async function fetchResults(filename: string) {
  if (!OCI_RESULTS_URL) return null;
  const res = await fetch(`${OCI_RESULTS_URL}/${filename}`);
  if (!res.ok) return null;
  return res.text();
}

import type { NextApiRequest, NextApiResponse } from "next";

const API_BASE_URL =
  process.env.SMART_BUYER_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).json({ error: "method_not_allowed" });
  }

  try {
    const upstream = await fetch(`${API_BASE_URL}/v1/smart-buyer/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(req.body),
    });

    const body = await upstream.json().catch(() => ({}));
    return res.status(upstream.status).json(body);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown upstream error";
    return res
      .status(502)
      .json({ error: "smart_buyer_upstream_error", message });
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retryOnAuth = true
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string> | undefined),
  };

  const res = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && retryOnAuth && !path.includes("/auth/")) {
    const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (refreshRes.ok) {
      return apiFetch<T>(path, options, false);
    }
  }

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new ApiError(message, res.status);
  }

  if (res.status === 204) {
    return {} as T;
  }
  return (await res.json()) as T;
}

export function getExportUrl(paperId: string, format: "paper_pdf" | "answer_key_pdf"): string {
  return `${API_BASE}/papers/${paperId}/export?format=${format}`;
}

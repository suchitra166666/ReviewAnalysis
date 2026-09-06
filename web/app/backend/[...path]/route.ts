import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const API = (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const dest = `${API}/${params.path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  const init: RequestInit = { method: req.method, headers, redirect: "manual" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }
  const res = await fetch(dest, init);
  const out = new Headers(res.headers);
  out.delete("content-encoding");
  out.delete("transfer-encoding");
  return new Response(res.body, { status: res.status, headers: out });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;

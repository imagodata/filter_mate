// The free quota of the FilterMate agent: a relay to the Messages API that spends a fixed budget, then says so.
// It keeps counters and never the content of a request.
import { DurableObject } from "cloudflare:workers";

import { Ledger, validLimits } from "./ledger.js";
import { MAX_BODY, MAX_OUTPUT, StreamMeter, amountToCharge, buildUpstreamBody, groupOfAddress, hasPrice, worstCase } from "./rules.js";

const API_VERSION = "2026-10-21";
const TOKEN_PREFIX = "fmq1";
const UPSTREAM_HEADERS_TIMEOUT_MS = 60000;
const encoder = new TextEncoder();

function limitsFrom(env) {
  const micros = (name) => Math.round(Number(env[name]) * 1e6);
  return { budget: micros("MONTHLY_BUDGET_USD"), user: micros("USER_MONTHLY_USD"), ip: micros("IP_MONTHLY_USD") };
}

export class QuotaLedger extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ledger = new Ledger(ctx.storage, limitsFrom(env));
  }

  register(ip) {
    return this.ledger.register(ip);
  }

  reserve(user, ip, amount) {
    return this.ledger.reserve(user, ip, amount);
  }

  settle(id, amount) {
    return this.ledger.settle(id, amount);
  }
}

function failure(status, type, message, headers = {}) {
  return new Response(JSON.stringify({ type: "error", error: { type, message } }), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

function base64Url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function fromBase64Url(text) {
  return Uint8Array.from(atob(text.replaceAll("-", "+").replaceAll("_", "/")), (char) => char.charCodeAt(0));
}

function signingKey(secret, use) {
  return crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, [use]);
}

async function newToken(secret) {
  const id = base64Url(crypto.getRandomValues(new Uint8Array(16)));
  const signature = await crypto.subtle.sign("HMAC", await signingKey(secret, "sign"), encoder.encode(id));
  return `${TOKEN_PREFIX}.${id}.${base64Url(new Uint8Array(signature))}`;
}

/** The id inside a token, null when it was not made here. */
async function verifiedUser(token, secret) {
  const [prefix, id, signature, extra] = (token || "").split(".");
  if (prefix !== TOKEN_PREFIX || !id || !signature || extra !== undefined) return null;
  try {
    const valid = await crypto.subtle.verify("HMAC", await signingKey(secret, "verify"), fromBase64Url(signature), encoder.encode(id));
    return valid ? id : null;
  } catch {
    return null;
  }
}

/** An IP address is only ever kept as this; an IPv6 address counts for its whole /64. */
async function ipId(request, secret) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(`${secret}:${groupOfAddress(request.headers.get("cf-connecting-ip") || "unknown")}`));
  return base64Url(new Uint8Array(digest)).slice(0, 22);
}

async function readCapped(request) {
  const declared = Number(request.headers.get("content-length") || 0);
  if (declared > MAX_BODY) return null;
  if (request.body === null) return new Uint8Array();
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const joined = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    joined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return joined;
}

function ledgerOf(env) {
  return env.LEDGER.get(env.LEDGER.idFromName("global"));
}

async function register(request, env) {
  if (!(await ledgerOf(env).register(await ipId(request, env.TOKEN_SECRET)))) {
    return failure(429, "rate_limit_error", "Too many new accounts from this address today.", { "retry-after": "86400" });
  }
  return new Response(JSON.stringify({ token: await newToken(env.TOKEN_SECRET) }), { headers: { "content-type": "application/json" } });
}

const REFUSALS = {
  budget: [402, "The free quota of FilterMate is used up for this month. Enter your own API key in the agent settings."],
  quota: [402, "Your free quota is used up for this month. Enter your own API key in the agent settings."],
  rate: [429, "Too many requests on the free quota: try again in a moment."],
};

async function messages(request, env, ctx) {
  const user = await verifiedUser(request.headers.get("x-api-key"), env.TOKEN_SECRET);
  if (user === null) return failure(401, "authentication_error", "Invalid access token.");
  const raw = await readCapped(request);
  if (raw === null) return failure(413, "invalid_request_error", "This conversation is too long for the free quota. Start a new one, or turn off some connectors.");
  const { body, problem } = buildUpstreamBody(new TextDecoder().decode(raw), env.MODEL);
  if (problem) return failure(400, "invalid_request_error", problem);
  body.metadata = { user_id: user }; // lets an abuse be traced to one token rather than to the whole account
  const outgoing = encoder.encode(JSON.stringify(body));
  const reserved = worstCase(env.MODEL, outgoing.byteLength, Math.min(body.max_tokens, MAX_OUTPUT));
  const ledger = ledgerOf(env);
  const reservation = await ledger.reserve(user, await ipId(request, env.TOKEN_SECRET), reserved);
  if (reservation.refused) {
    const [status, message] = REFUSALS[reservation.refused];
    return failure(status, status === 402 ? "insufficient_quota" : "rate_limit_error", message, status === 429 ? { "retry-after": "20" } : {});
  }
  let upstream;
  const abort = new AbortController();
  const headersTimer = setTimeout(() => abort.abort(), UPSTREAM_HEADERS_TIMEOUT_MS);
  try {
    upstream = await fetch(`${env.UPSTREAM}/v1/messages`, {
      method: "POST",
      redirect: "manual", // a redirect is a failure like any other: the key must not follow it
      signal: abort.signal,
      headers: { "content-type": "application/json", accept: "text/event-stream", "anthropic-version": API_VERSION, "x-api-key": env.ANTHROPIC_API_KEY },
      body: outgoing,
    });
  } catch {
    ctx.waitUntil(ledger.settle(reservation.id, 0));
    return failure(502, "api_error", "The model could not be reached.");
  } finally {
    clearTimeout(headersTimer);
  }
  if (!upstream.ok) {
    ctx.waitUntil(ledger.settle(reservation.id, 0));
    const kind = await upstream.json().then((data) => data?.error?.type, () => "unreadable");
    console.log(`upstream status ${upstream.status} ${String(kind).slice(0, 40)}`); // never its message: it can name the account
    if (upstream.status === 429) return failure(429, "rate_limit_error", "The free quota is busy: try again in a moment.", { "retry-after": "20" });
    if (upstream.status === 400) return failure(400, "invalid_request_error", "The model refused this request.");
    return failure(503, "overloaded_error", "The free quota is unavailable for now.");
  }
  const meter = new StreamMeter();
  const reader = upstream.body.getReader();
  let settled = false;
  const finish = () => {
    if (!settled) {
      settled = true;
      ctx.waitUntil(ledger.settle(reservation.id, amountToCharge(env.MODEL, meter, reserved, body.max_tokens)));
    }
  };
  const stream = new ReadableStream({
    async pull(controller) {
      try {
        const { value, done } = await reader.read();
        if (done) {
          finish();
          const rest = meter.flush();
          if (rest.byteLength) controller.enqueue(rest);
          controller.close();
          return;
        }
        const passed = meter.feed(value);
        if (passed.byteLength) controller.enqueue(passed);
      } catch (error) {
        finish();
        controller.error(error);
      }
    },
    async cancel() {
      finish(); // the model stops with this connection: the prompt, and what it can have written
      await reader.cancel();
    },
  });
  return new Response(stream, { headers: { "content-type": "text/event-stream", "cache-control": "no-cache" } });
}

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    if (pathname === "/health") return new Response("ok");
    if (request.method !== "POST" || !["/v1/register", "/v1/messages"].includes(pathname)) return failure(404, "not_found_error", "Not found.");
    if (env.DISABLED || !hasPrice(env.MODEL) || !env.ANTHROPIC_API_KEY || !env.TOKEN_SECRET || !validLimits(limitsFrom(env))) {
      return failure(503, "overloaded_error", "The free quota is unavailable for now.");
    }
    if (env.LIMITER) { // before the ledger: a refused client must not cost a Durable Object request each time
      const { success } = await env.LIMITER.limit({ key: groupOfAddress(request.headers.get("cf-connecting-ip") || "unknown") });
      if (!success) return failure(429, "rate_limit_error", "Too many requests: try again in a moment.", { "retry-after": "20" });
    }
    return pathname === "/v1/register" ? register(request, env) : messages(request, env, ctx);
  },
};

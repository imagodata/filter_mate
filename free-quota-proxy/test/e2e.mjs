// The real Worker in the local runtime, against a fake model: nothing leaves this machine and no model is called.
//   npm install && npm run e2e
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";

const UP_PORT = 18798;
const WORKER_PORT = 18799;
const BASE = `http://127.0.0.1:${WORKER_PORT}`;
const SERVER_KEY = "server-side-key-for-the-test";
const seen = [];
const plan = { status: 200 };

const sse = 'event: message_start\ndata: {"type":"message_start","message":{"usage":{"input_tokens":1000,"output_tokens":1}}}\n\nevent: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":5000}}\n\nevent: message_stop\ndata: {"type":"message_stop"}\n\n';

const upstream = createServer((request, response) => {
  let text = "";
  request.on("data", (chunk) => { text += chunk; });
  request.on("end", () => {
    seen.push({ headers: request.headers, body: JSON.parse(text), url: request.url });
    if (plan.status !== 200) {
      response.writeHead(plan.status, { "content-type": "application/json" });
      response.end('{"type":"error","error":{"type":"authentication_error","message":"account of Simon: invalid key"}}');
      return;
    }
    response.writeHead(200, { "content-type": "text/event-stream" });
    // In small pieces, as the real API sends them: an event is often split between two reads.
    const bytes = Buffer.from(sse);
    let at = 0;
    const next = () => {
      if (at >= bytes.length) {
        response.end();
        return;
      }
      response.write(bytes.subarray(at, at + 7));
      at += 7;
      setTimeout(next, 2);
    };
    next();
  });
});
await new Promise((resolve) => upstream.listen(UP_PORT, "127.0.0.1", resolve));

const worker = spawn("npx", ["wrangler", "dev", "--port", String(WORKER_PORT), "--ip", "127.0.0.1", "--log-level", "warn", "--persist-to", mkdtempSync(join(tmpdir(), "fm-quota-")),
  "--var", `UPSTREAM:http://127.0.0.1:${UP_PORT}`, "--var", `ANTHROPIC_API_KEY:${SERVER_KEY}`, "--var", "TOKEN_SECRET:test-secret-0123456789",
  "--var", "USER_MONTHLY_USD:0.02", "--var", "IP_MONTHLY_USD:0.5"], { stdio: ["ignore", "pipe", "pipe"], env: { ...process.env, WRANGLER_SEND_METRICS: "false" }, detached: true });
let log = "";
worker.stdout.on("data", (chunk) => { log += chunk; });
worker.stderr.on("data", (chunk) => { log += chunk; });

let passed = 0;
function check(label, run) {
  try {
    run();
    passed += 1;
    console.log(`PASS ${label}`);
  } catch (error) {
    console.log(`FAIL ${label}: ${error.message}`);
    process.exitCode = 1;
  }
}

function body(changes = {}) {
  return JSON.stringify({
    stream: true, max_tokens: 16000, system: [{ type: "text", text: "You are the FilterMate assistant, here." }],
    tools: ["list_layers", "describe_layer", "apply_filter"].map((name) => ({ name, description: "d", input_schema: { type: "object" } })),
    messages: [{ role: "user", content: [{ type: "text", text: "hello" }] }], ...changes,
  });
}

const post = (path, text, headers = {}) => fetch(BASE + path, { method: "POST", body: text, headers: { "content-type": "application/json", ...headers } });

try {
  let ready = false;
  for (let i = 0; i < 120 && !ready; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    try { ready = (await fetch(`${BASE}/health`)).ok; } catch { /* not yet */ }
  }
  check("the Worker starts", () => assert.ok(ready, log));

  const anonymous = (await post("/v1/messages", body())).status;
  const forged = (await post("/v1/messages", body(), { "x-api-key": "fmq1.aaaa.bbbb" })).status;
  check("no token, no model", () => { assert.equal(anonymous, 401); assert.equal(forged, 401); assert.equal(seen.length, 0); });

  const registered = await post("/v1/register", "{}");
  const { token } = await registered.json();
  check("a token is given", () => assert.ok(token.startsWith("fmq1.")));
  const headers = { "x-api-key": token };

  const answer = await post("/v1/messages", body({ model: "claude-opus-5-5", tools: undefined }), headers);
  check("another use is refused before the model", () => { assert.equal(answer.status, 400); assert.equal(seen.length, 0); });

  const served = await post("/v1/messages", body({ model: "claude-opus-5-5" }), { ...headers, "anthropic-beta": "x", "x-other": "y" });
  const text = await served.text();
  check("the stream passes untouched", () => { assert.equal(served.status, 200); assert.equal(text, sse); });
  check("its model, its key, the client's token never", () => {
    assert.equal(seen[0].body.model, "claude-haiku-5-5");
    assert.equal(seen[0].headers["x-api-key"], SERVER_KEY);
    assert.equal(seen[0].headers["anthropic-beta"], undefined);
    assert.equal(seen[0].headers["x-other"], undefined);
    assert.equal(seen[0].body.max_tokens, 8192);
    assert.ok(!JSON.stringify(seen[0]).includes(token));
    assert.ok(seen[0].body.metadata.user_id && !token.endsWith(seen[0].body.metadata.user_id));
  });

  plan.status = 401;
  const hidden = await post("/v1/messages", body(), headers);
  const hiddenText = await hidden.text();
  check("a failure upstream says nothing of the account", () => { assert.equal(hidden.status, 503); assert.ok(!hiddenText.includes("Simon")); });
  plan.status = 429;
  const busy = (await post("/v1/messages", body(), headers)).status;
  check("busy upstream is a wait", () => assert.equal(busy, 429));
  plan.status = 200;

  let refused = null;
  for (let i = 0; i < 9 && refused === null; i += 1) {
    const reply = await post("/v1/messages", body(), headers);
    if (reply.status === 402) refused = await reply.json();
    else await reply.text();
    await new Promise((resolve) => setTimeout(resolve, 6500));
  }
  check("the quota of a user ends, and says what to do", () => {
    assert.ok(refused, "never refused");
    assert.equal(refused.error.type, "insufficient_quota");
    assert.ok(refused.error.message.includes("own API key"));
  });

  const before = seen.length;
  const other = await (await post("/v1/register", "{}")).json();
  const fresh = await post("/v1/messages", body(), { "x-api-key": other.token });
  await fresh.text();
  check("another user still has theirs", () => { assert.equal(fresh.status, 200); assert.equal(seen.length, before + 1); });
  console.log(`${passed} checks passed`);
} catch (error) {
  console.log(`FAIL ${error.stack}\n${log}`);
  process.exitCode = 1;
} finally {
  try { process.kill(-worker.pid); } catch { /* gone */ }
  upstream.close();
  setTimeout(() => process.exit(), 300);
}

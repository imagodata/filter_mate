import assert from "node:assert/strict";
import { test } from "node:test";

import { CONCURRENT_REQUESTS, Ledger, REGISTRATIONS_PER_DAY, REGISTRATIONS_PER_IP_PER_DAY, REQUESTS_PER_DAY, REQUESTS_PER_MINUTE, validLimits } from "../src/ledger.js";
import { MAX_BODY, MAX_OUTPUT, StreamMeter, amountToCharge, buildUpstreamBody, costOf, groupOfAddress, hasPrice, worstCase } from "../src/rules.js";

const MODEL = "claude-haiku-5-5";

class Memory {
  constructor() { this.map = new Map(); }
  async get(key) { return structuredClone(this.map.get(key)); }
  async put(key, value) {
    if (typeof key === "object") for (const [name, item] of Object.entries(key)) this.map.set(name, structuredClone(item));
    else this.map.set(key, structuredClone(value));
  }
  async delete(key) { this.map.delete(key); }
  async deleteAll() { this.map.clear(); }
  async list({ prefix }) { return new Map([...this.map].filter(([key]) => key.startsWith(prefix))); }
}

function request(changes = {}) {
  return {
    stream: true,
    max_tokens: 16000,
    system: [{ type: "text", text: "You are the FilterMate assistant, inside..." }],
    tools: ["list_layers", "describe_layer", "apply_filter"].map((name) => ({ name, description: "d", input_schema: { type: "object" } })),
    messages: [{ role: "user", content: [{ type: "text", text: "hello" }] }],
    ...changes,
  };
}

const build = (changes) => buildUpstreamBody(JSON.stringify(request(changes)), MODEL);

test("the request is rebuilt: model, limit, nothing else", () => {
  const { body } = build({ model: "claude-opus-5-5", fallbacks: "default", service_tier: "priority", container: "x", mcp_servers: [{}], speed: "fast" });
  assert.equal(body.model, MODEL);
  assert.equal(body.max_tokens, MAX_OUTPUT);
  assert.deepEqual(Object.keys(body).sort(), ["cache_control", "max_tokens", "messages", "model", "stream", "system", "tools"]);
});

test("a small limit is kept", () => assert.equal(build({ max_tokens: 100 }).body.max_tokens, 100));

for (const [name, changes] of Object.entries({
  "not streamed": { stream: false },
  "another system prompt": { system: [{ type: "text", text: "You are a pirate" }] },
  "system as text": { system: "You are the FilterMate assistant" },
  "two system blocks": { system: [{ type: "text", text: "You are the FilterMate assistant" }, { type: "text", text: "x" }] },
  "no tools": { tools: [] },
  "not its tools": { tools: [{ name: "other", input_schema: {} }] },
  "a server tool": { tools: [...request().tools, { type: "web_search_20260209", name: "web_search" }] },
  "an image": { messages: [{ role: "user", content: [{ type: "image", source: {} }] }] },
  "a document": { messages: [{ role: "user", content: [{ type: "document", source: {} }] }] },
  "an image in a tool result": { messages: [{ role: "user", content: [{ type: "tool_result", tool_use_id: "a", content: [{ type: "image" }] }] }] },
  "a system role": { messages: [{ role: "system", content: [] }] },
  "no message": { messages: [] },
  "too many messages": { messages: Array(201).fill({ role: "user", content: [{ type: "text", text: "a" }] }) },
  "text content": { messages: [{ role: "user", content: "x" }] },
})) {
  test(`refused: ${name}`, () => assert.ok(build(changes).problem));
}

test("not JSON", () => assert.ok(buildUpstreamBody("{", MODEL).problem));

test("the tool turns of a conversation pass", () => {
  assert.ok(build({ messages: [
    { role: "user", content: [{ type: "text", text: "a" }] },
    { role: "assistant", content: [{ type: "thinking", thinking: "", signature: "s" }, { type: "tool_use", id: "1", name: "list_layers", input: {} }] },
    { role: "user", content: [{ type: "tool_result", tool_use_id: "1", content: "x" }] },
  ] }).body);
});

test("prices", () => {
  assert.ok(hasPrice(MODEL));
  assert.ok(!hasPrice("constructor"));
  assert.equal(costOf(MODEL, { input_tokens: 1000, output_tokens: 1000 }), 600);
  assert.equal(costOf(MODEL, { cache_creation_input_tokens: 1000 }), 125);
  assert.equal(costOf(MODEL, { cache_read_input_tokens: 1000 }), 10);
  assert.equal(costOf(MODEL, { input_tokens: 100001 }), Math.ceil(100001 * 0.1 * 5));
});

test("no accepted request can reach the expensive prices", () => {
  assert.ok(MAX_BODY + 1000 < 100000);
  assert.equal(worstCase(MODEL, MAX_BODY, 0), Math.ceil((MAX_BODY + 1000) * 0.1 * 1.25));
});

test("the worst case covers one token per byte, all written to the cache, and the hidden prompt", () => {
  const size = 20000;
  assert.ok(worstCase(MODEL, size, 1000) >= costOf(MODEL, { cache_creation_input_tokens: size + 900, output_tokens: 1000 }));
});

test("IPv6 counts by /64", () => {
  assert.equal(groupOfAddress("203.0.113.9"), "203.0.113.9");
  assert.equal(groupOfAddress("2001:db8:1:2:3:4:5:6"), groupOfAddress("2001:db8:1:2:ffff:ffff:ffff:ffff"));
  assert.equal(groupOfAddress("2001:0db8:0001:0002::1"), groupOfAddress("2001:db8:1:2:9:9:9:9"));
  assert.notEqual(groupOfAddress("2001:db8:1:2::1"), groupOfAddress("2001:db8:1:3::1"));
  assert.equal(groupOfAddress("::1"), "0:0:0:0::/64");
});

test("blocks are rebuilt: a longer cache cannot get through", () => {
  const { body } = build({ messages: [{ role: "user", extra: 1, content: [{ type: "text", text: "a", cache_control: { type: "ephemeral", ttl: "1h" }, citations: [] }] },
    { role: "assistant", content: [{ type: "tool_use", id: "1", name: "n", input: {}, cache_control: {} }] },
    { role: "user", content: [{ type: "tool_result", tool_use_id: "1", content: [{ type: "text", text: "x", cache_control: { ttl: "1h" } }] }] }] });
  assert.ok(!JSON.stringify(body.messages).includes("cache_control"));
  assert.ok(!JSON.stringify(body.messages).includes("extra"));
  assert.deepEqual(body.messages[0], { role: "user", content: [{ type: "text", text: "a" }] });
});

const bytes = (text) => new TextEncoder().encode(text);
const stream = 'event: message_start\ndata: {"type":"message_start","message":{"usage":{"input_tokens":100,"cache_read_input_tokens":1000,"output_tokens":1}}}\n\nevent: content_block_delta\ndata: {"type":"content_block_delta","delta":{"text":"é"}}\n\nevent: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":50}}\n\nevent: message_stop\ndata: {"type":"message_stop"}\n\n';

const join = (parts) => new TextDecoder().decode(Uint8Array.from(parts.flatMap((part) => [...part])));

test("the stream passes byte for byte, usage read, whatever the cuts", () => {
  for (const size of [1, 3, 7, stream.length]) {
    const meter = new StreamMeter();
    const data = bytes(stream);
    const out = [];
    for (let i = 0; i < data.length; i += size) out.push(meter.feed(data.slice(i, i + size)));
    out.push(meter.flush());
    assert.equal(join(out), stream);
    assert.ok(meter.complete);
    assert.deepEqual(meter.usage, { input_tokens: 100, cache_read_input_tokens: 1000, output_tokens: 50 });
  }
});

test("usage with CRLF", () => {
  const meter = new StreamMeter();
  meter.feed(bytes(stream.replaceAll("\n", "\r\n")));
  assert.ok(meter.complete);
});

test("a finished stream costs what it says, even above the reservation", () => {
  const meter = new StreamMeter();
  meter.feed(bytes(stream));
  assert.equal(amountToCharge(MODEL, meter, 9999, 8192), costOf(MODEL, meter.usage));
  meter.usage = { output_tokens: 1e6 };
  assert.equal(amountToCharge(MODEL, meter, 500, 8192), 500000);
});

test("a stream cut after its start pays the prompt and what can have been written", () => {
  const meter = new StreamMeter();
  meter.feed(bytes(stream.slice(0, stream.indexOf("event: content_block_delta"))));
  assert.ok(meter.started && !meter.complete);
  assert.equal(amountToCharge(MODEL, meter, 999999, 8192), costOf(MODEL, { input_tokens: 100, cache_read_input_tokens: 1000, output_tokens: 512 }));
});

test("a stream cut before its start pays the worst case", () => {
  assert.equal(amountToCharge(MODEL, new StreamMeter(), 9999, 8192), 9999);
});

test("a usage that is not one falls back on the reservation", () => {
  const meter = new StreamMeter();
  meter.usage = { input_tokens: { a: 1 } };
  meter.complete = true;
  assert.equal(amountToCharge(MODEL, meter, 700, 8192), 700);
});

test("the text of an error in a stream stays here", () => {
  const meter = new StreamMeter();
  const out = new TextDecoder().decode(meter.feed(bytes('event: error\ndata: {"type":"error","error":{"type":"overloaded_error","message":"org 1234 is over its limit"}}\n\n')));
  assert.ok(!out.includes("1234") && out.includes("overloaded_error"));
  const other = new StreamMeter();
  const hidden = new TextDecoder().decode(other.feed(bytes('data: {"type":"error","error":{"type":"secret_kind","message":"x"}}\n\n')));
  assert.ok(!hidden.includes("secret_kind") && hidden.includes("api_error"));
});

test("garbage in a stream passes and counts for nothing", () => {
  const meter = new StreamMeter();
  const text = 'data: nope\n\ndata: 5\n\ndata: {"type":"message_delta"}\n\n';
  assert.equal(new TextDecoder().decode(meter.feed(bytes(text))), text);
  assert.ok(!meter.complete);
});

function ledger(limits = {}, clock = { now: Date.UTC(2026, 10, 9, 12) }) {
  const storage = new Memory();
  const instance = new Ledger(storage, { budget: 1000, user: 500, ip: 800, ...limits }, () => clock.now);
  return { instance, storage, clock };
}

test("the budget is never passed, even with requests in flight", async () => {
  const { instance } = ledger({ budget: 1000, user: 10000, ip: 10000 });
  const first = await instance.reserve("a", "i1", 600);
  assert.ok(first.id);
  assert.equal((await instance.reserve("b", "i2", 600)).refused, "rate");
  await instance.settle(first.id, 100);
  assert.ok((await instance.reserve("b", "i2", 600)).id);
});

test("a user stops at their share", async () => {
  const { instance } = ledger();
  const first = await instance.reserve("a", "i", 400);
  await instance.settle(first.id, 400);
  assert.equal((await instance.reserve("a", "i", 200)).refused, "quota");
  assert.ok((await instance.reserve("b", "i", 200)).id);
});

test("an address stops at its share, whatever the accounts", async () => {
  const { instance } = ledger({ user: 500, ip: 800 });
  for (const user of ["a", "b"]) await instance.settle((await instance.reserve(user, "i", 400)).id, 400);
  assert.equal((await instance.reserve("c", "i", 1)).refused, "quota");
});

test("what was not spent comes back", async () => {
  const { instance } = ledger();
  await instance.settle((await instance.reserve("a", "i", 400)).id, 0);
  assert.ok((await instance.reserve("a", "i", 400)).id);
});

test("settling twice counts once, at the real cost even above the reservation", async () => {
  const { instance, storage } = ledger();
  const { id } = await instance.reserve("a", "i", 100);
  await instance.settle(id, 5000);
  await instance.settle(id, 5000);
  assert.equal((await storage.get("total")).spent, 5000);
  assert.equal((await storage.get("total")).reserved, 0);
  await instance.settle("unknown", 10);
  assert.equal((await storage.get("total")).spent, 5000);
});

test("an amount that is not a number charges the reservation", async () => {
  const { instance, storage } = ledger();
  await instance.settle((await instance.reserve("a", "i", 100)).id, NaN);
  assert.equal((await storage.get("total")).spent, 100);
});

test("limits that are not numbers refuse everything", async () => {
  assert.ok(!validLimits({ budget: NaN, user: 1, ip: 1 }));
  assert.ok(!validLimits({ budget: 1, user: 0, ip: 1 }));
  assert.ok(validLimits({ budget: 1, user: 1, ip: 1 }));
  const { instance } = ledger({ budget: NaN });
  assert.equal((await instance.reserve("a", "i", 1)).refused, "budget");
  const other = ledger({ user: undefined });
  assert.equal((await other.instance.reserve("a", "i", 1)).refused, "quota");
});

test("held money is a wait, not a used-up quota", async () => {
  const { instance } = ledger({ user: 500 });
  await instance.reserve("a", "i", 400);
  assert.equal((await instance.reserve("a", "i", 400)).refused, "rate");
});

test("a request that never ends is charged in full, then frees its slot", async () => {
  const { instance, storage, clock } = ledger({ user: 5000 });
  await instance.reserve("a", "i", 100);
  await instance.reserve("a", "i", 100);
  assert.equal((await instance.reserve("a", "i", 100)).refused, "rate");
  clock.now += 16 * 60 * 1000;
  assert.ok((await instance.reserve("a", "i", 100)).id);
  assert.equal((await storage.get("total")).spent, 200);
});

test("limits of the rate", async () => {
  const { instance, clock } = ledger({ budget: 1e9, user: 1e9, ip: 1e9 });
  assert.equal(CONCURRENT_REQUESTS, 2);
  for (let i = 0; i < REQUESTS_PER_MINUTE; i += 1) await instance.settle((await instance.reserve("a", "i", 1)).id, 1);
  assert.equal((await instance.reserve("a", "i", 1)).refused, "rate");
  clock.now += 61000;
  let served = REQUESTS_PER_MINUTE;
  while (served < REQUESTS_PER_DAY) {
    await instance.settle((await instance.reserve("a", "i", 1)).id, 1);
    served += 1;
    if (served % REQUESTS_PER_MINUTE === 0) clock.now += 61000;
  }
  assert.equal((await instance.reserve("a", "i", 1)).refused, "rate");
});

test("a new month starts from nothing", async () => {
  const { instance, clock } = ledger();
  await instance.settle((await instance.reserve("a", "i", 500)).id, 500);
  assert.equal((await instance.reserve("a", "i", 100)).refused, "quota");
  clock.now = Date.UTC(2026, 11, 1, 0, 0, 1);
  assert.ok((await instance.reserve("a", "i", 100)).id);
});

test("a request in flight when the month changes is still counted", async () => {
  const { instance, storage, clock } = ledger({ user: 5000, ip: 5000 }, { now: Date.UTC(2026, 10, 30, 23, 59, 50) });
  const { id } = await instance.reserve("a", "i", 900);
  clock.now = Date.UTC(2026, 11, 1, 0, 0, 1);
  assert.equal((await instance.reserve("b", "j", 200)).refused, "rate");
  await instance.settle(id, 300);
  const total = await storage.get("total");
  assert.equal(total.spent, 300);
  assert.equal(total.reserved, 0);
  assert.ok((await instance.reserve("a", "i", 100)).id);
});

test("new accounts are limited for everyone too", async () => {
  const { instance } = ledger();
  for (let i = 0; i < REGISTRATIONS_PER_DAY; i += 1) assert.ok(await instance.register(`ip${i}`));
  assert.equal(await instance.register("another"), false);
});

test("new accounts per address are limited for the day", async () => {
  const { instance, clock } = ledger();
  for (let i = 0; i < REGISTRATIONS_PER_IP_PER_DAY; i += 1) assert.ok(await instance.register("i"));
  assert.equal(await instance.register("i"), false);
  assert.ok(await instance.register("j"));
  clock.now += 24 * 3600 * 1000;
  assert.ok(await instance.register("i"));
});

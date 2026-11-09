// What this relay accepts and what a request costs. No Worker API here: `node --test` runs it.

// Below the size where a prompt costs five times as much, whatever its density: at most one token per byte.
export const MAX_BODY = 90000;
export const MAX_OUTPUT = 8192;
const HIDDEN_PROMPT_TOKENS = 1000; // what the API adds around the tools
const CUT_MARGIN_TOKENS = 512; // what the model may have written after the last byte seen
const MAX_MESSAGES = 200;
const MAX_TOOLS = 90;
const MAX_EVENT = 1024 * 1024;
const SAFE_ERRORS = new Set(["overloaded_error", "rate_limit_error", "api_error"]);
const SYSTEM_START = "You are the FilterMate assistant";
const REQUIRED_TOOLS = ["list_layers", "describe_layer", "apply_filter"];
// Each block is rebuilt from these fields: anything else, a one-hour cache for instance, would cost what is not counted.
const BLOCK_FIELDS = {
  text: ["type", "text"],
  tool_use: ["type", "id", "name", "input"],
  tool_result: ["type", "tool_use_id", "content", "is_error"],
  thinking: ["type", "thinking", "signature"],
  redacted_thinking: ["type", "data"],
};

// Dollars per million tokens. Check them against the price page when the model changes.
const PRICES = {
  "claude-haiku-5-5": { input: 0.1, output: 0.5, premiumFactor: 5, premiumAbove: 100000 },
};
const CACHE_WRITE = 1.25;
const CACHE_READ = 0.1;

/** What counts as one address: a whole IPv6 /64, which a single machine commonly holds. */
export function groupOfAddress(address) {
  if (!address.includes(":")) return address;
  const [left, right = ""] = address.toLowerCase().split("::");
  const head = left ? left.split(":") : [];
  const tail = right ? right.split(":") : [];
  const full = address.includes("::") ? [...head, ...Array(Math.max(0, 8 - head.length - tail.length)).fill("0"), ...tail] : head;
  return `${full.slice(0, 4).map((part) => part.replace(/^0+(?=.)/, "")).join(":")}::/64`;
}

export function hasPrice(model) {
  return Object.prototype.hasOwnProperty.call(PRICES, model);
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function pick(source, fields) {
  const kept = {};
  for (const name of fields) if (source[name] !== undefined) kept[name] = source[name];
  return kept;
}

function cleanBlock(block) {
  if (!isObject(block) || !Object.prototype.hasOwnProperty.call(BLOCK_FIELDS, block.type)) return null; // images and documents are not counted in bytes
  const kept = pick(block, BLOCK_FIELDS[block.type]);
  if (block.type !== "tool_result") return kept;
  if (typeof kept.content === "string") return kept;
  if (!Array.isArray(kept.content)) return null;
  if (kept.content.some((part) => !isObject(part) || part.type !== "text")) return null;
  kept.content = kept.content.map((part) => pick(part, BLOCK_FIELDS.text));
  return kept;
}

/** The messages, rebuilt field by field, or null. */
function cleanMessages(messages) {
  if (!Array.isArray(messages) || messages.length === 0 || messages.length > MAX_MESSAGES) return null;
  const cleaned = [];
  for (const message of messages) {
    if (!isObject(message) || !["user", "assistant"].includes(message.role) || !Array.isArray(message.content)) return null;
    const content = message.content.map(cleanBlock);
    if (content.includes(null)) return null;
    cleaned.push({ role: message.role, content });
  }
  return cleaned;
}

function cleanTools(tools) {
  if (!Array.isArray(tools) || tools.length === 0 || tools.length > MAX_TOOLS) return null;
  const cleaned = [];
  for (const tool of tools) {
    // A tool with a `type` is a server tool, billed per use: web search, code execution.
    if (!isObject(tool) || tool.type !== undefined || typeof tool.name !== "string" || !isObject(tool.input_schema)) return null;
    cleaned.push({ name: tool.name, description: String(tool.description ?? ""), input_schema: tool.input_schema });
  }
  const names = new Set(cleaned.map((tool) => tool.name));
  return REQUIRED_TOOLS.every((name) => names.has(name)) ? cleaned : null;
}

/** The request to send upstream, rebuilt field by field, or the reason it is refused. */
export function buildUpstreamBody(text, model) {
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    return { problem: "not JSON" };
  }
  if (!isObject(body) || body.stream !== true) return { problem: "a streamed request is expected" };
  const system = body.system;
  if (!Array.isArray(system) || system.length !== 1 || !isObject(system[0]) || system[0].type !== "text"
      || typeof system[0].text !== "string" || !system[0].text.startsWith(SYSTEM_START)) {
    return { problem: "this service only answers the FilterMate plugin" };
  }
  const tools = cleanTools(body.tools);
  if (tools === null) return { problem: "this service only answers the FilterMate plugin" };
  const messages = cleanMessages(body.messages);
  if (messages === null) return { problem: "invalid messages" };
  const asked = Number.isInteger(body.max_tokens) && body.max_tokens > 0 ? body.max_tokens : MAX_OUTPUT;
  return {
    body: {
      model,
      max_tokens: Math.min(asked, MAX_OUTPUT),
      stream: true,
      cache_control: { type: "ephemeral" },
      system: [{ type: "text", text: system[0].text }],
      tools,
      messages,
    },
  };
}

/** The most a request can cost, in millionths of a dollar: at most one token per byte, all written to the cache. */
export function worstCase(model, bytes, maxTokens) {
  const price = PRICES[model];
  const tokens = bytes + HIDDEN_PROMPT_TOKENS;
  const factor = tokens > price.premiumAbove ? price.premiumFactor : 1;
  return Math.ceil(tokens * price.input * factor * CACHE_WRITE + maxTokens * price.output * factor);
}

/** What a finished request cost, in millionths of a dollar. */
export function costOf(model, usage) {
  const price = PRICES[model];
  const input = usage.input_tokens || 0;
  const written = usage.cache_creation_input_tokens || 0;
  const read = usage.cache_read_input_tokens || 0;
  const factor = input + written + read > price.premiumAbove ? price.premiumFactor : 1;
  return Math.ceil((input * price.input + written * price.input * CACHE_WRITE + read * price.input * CACHE_READ
    + (usage.output_tokens || 0) * price.output) * factor);
}

/**
 * Passes a Messages stream through, event by event: bytes unchanged, usage read on the way.
 * Only the text of an error is replaced: it comes from the account of the relay.
 */
export class StreamMeter {
  constructor() {
    this.decoder = new TextDecoder();
    this.encoder = new TextEncoder();
    this.pending = "";
    this.usage = {};
    this.started = false;
    this.complete = false;
    this.outputBytes = 0;
  }

  feed(chunk) {
    this.pending += this.decoder.decode(chunk, { stream: true });
    let out = "";
    for (;;) {
      const end = /\r\n\r\n|\n\n|\r\r/.exec(this.pending);
      if (end === null) break;
      const stop = end.index + end[0].length;
      out += this.pass(this.pending.slice(0, stop));
      this.pending = this.pending.slice(stop);
    }
    if (this.pending.length > MAX_EVENT) {
      out += this.pending;
      this.pending = "";
    }
    return this.encoder.encode(out);
  }

  flush() {
    const rest = this.pending;
    this.pending = "";
    return this.encoder.encode(rest);
  }

  pass(raw) {
    let event = null;
    for (const line of raw.split(/\r\n|\n|\r/)) {
      if (line.startsWith("data:")) {
        try {
          event = JSON.parse(line.slice(5).trim());
        } catch {
          return raw;
        }
      }
    }
    if (!isObject(event)) return raw;
    if (event.type === "message_start" && isObject(event.message?.usage)) {
      Object.assign(this.usage, event.message.usage);
      this.started = true;
    } else if (event.type === "message_delta" && isObject(event.usage)) {
      Object.assign(this.usage, event.usage);
      this.complete = true;
    } else if (event.type === "content_block_delta") {
      this.outputBytes += raw.length;
    } else if (event.type === "error") {
      const kind = SAFE_ERRORS.has(event.error?.type) ? event.error.type : "api_error";
      return `event: error\ndata: ${JSON.stringify({ type: "error", error: { type: kind, message: "The free quota is unavailable for now." } })}\n\n`;
    }
    return raw;
  }
}

/** What to charge when the stream ends. A cut one pays its prompt and what can have been written, not the whole answer. */
export function amountToCharge(model, meter, reserved, maxTokens) {
  let cost = reserved;
  if (meter.complete) {
    cost = costOf(model, meter.usage);
  } else if (meter.started) {
    const written = Math.min(maxTokens, meter.outputBytes + CUT_MARGIN_TOKENS);
    cost = costOf(model, { ...meter.usage, output_tokens: written });
  }
  return Number.isFinite(cost) && cost >= 0 ? cost : reserved; // a usage that is not one must not break the accounts
}

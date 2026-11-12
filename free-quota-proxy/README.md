# FilterMate free quota

A Cloudflare Worker that lets people try the agent of FilterMate without an API key. It relays the requests of the panel to the
Messages API with one server-side key, and stops at a fixed monthly budget. When it stops, the panel asks for the user's own key.

Deployed at https://filtermate-free-quota.filtermate-free-quota-proxy.workers.dev.

## Limits

| Limit | Default | Where |
|---|---|---|
| Whole service, per month | 200 $ | `MONTHLY_BUDGET_USD` |
| One access token, per month | 0.50 $ | `USER_MONTHLY_USD` |
| One IP address, per month | 2 $ | `IP_MONTHLY_USD` |
| New tokens per address, per day | 3, and 50 for everyone | `src/ledger.js` |
| Budget alerts | 50 %, 80 % and 95 % of the month, once each | `src/ledger.js`, `ALERT_WEBHOOK` |
| Requests per token | 2 at once, 30 per minute, 300 per day | `src/ledger.js` |
| Requests per address | 60 per minute, before any accounting | `wrangler.toml` |
| Answer length | 8192 tokens | `src/rules.js` |
| Request size | 90 kB, which keeps every prompt below the 100 000 tokens where the price is five times higher | `src/rules.js` |
| Model | Claude Haiku 5.5 | `MODEL` |

An IPv6 address counts for its whole /64. The limit per address is what really bounds one person: a token alone is easy to replace.
Addresses in large numbers, residential proxies for instance, get past it, up to 50 new tokens a day: 25 $ a day at most, so an
attack needs 8 days to spend the month. The monthly budget still holds, for everyone: watch the alerts.

When a part of the budget is spent, the Worker logs `{"alert":"budget","part":0.8}` once for the month. To receive it, set a
Slack or Discord incoming webhook: `npx wrangler secret put ALERT_WEBHOOK`. Set a spend limit on the Anthropic workspace of the key
as well: the counters are an estimate.

The budget is held before each request at the worst the request can cost, and replaced by the real cost when the stream says it.
A stream cut short pays its prompt and what can have been written. A request that never reports pays its worst case, after 15 minutes.

The counters are an estimate of the bill. They rest on the prices in `src/rules.js`, where cache writes are assumed to cost 1.25 times
the input price and cache reads 0.1 times. They do not include a data-residency multiplier, nor a request cut by a network failure
after Anthropic accepted it. Only one model has a price: another `MODEL` makes the service answer 503, as do limits that are missing
or not numbers.

**Set a spend limit on the workspace of the key in the Claude Console as well.** It is the only limit that does not depend on this
code.

## What the relay accepts

Only what the panel sends: a streamed request with the system prompt and the tools of FilterMate. The body is rebuilt field by
field, so a client cannot pick another model, a longer cache, a server tool billed per use, or send images. That is a brake against reuse as a
free general API, not a proof of identity: anyone can copy those fields, and the limits above are what bounds the cost.

## Privacy

The Worker keeps counters per access token and a salted hash of each IP address, reset every month. It keeps no prompt, answer or
raw IP address. Requests go on to Anthropic under the terms of the account that owns the key, which the panel asks the user to accept.

## Deploy

```sh
npm install
npx wrangler login
npx wrangler secret put ANTHROPIC_API_KEY   # a key in its own workspace, with a spend limit
npx wrangler secret put TOKEN_SECRET        # openssl rand -base64 32
npx wrangler deploy
```

Then set `FREE_QUOTA_URL` in `core/agent/providers/__init__.py` to the address of the Worker, and release the plugin. Do not use the
configuration file for this: it is copied into each profile once, and would not follow a later change. A user can still override
the address with `APP.OPTIONS.AGENT.free_quota_url`.

Changing `TOKEN_SECRET` invalidates every token: the panel asks for a new one by itself. To turn the service off, run
`npx wrangler secret put DISABLED` with any text; `npx wrangler secret delete DISABLED` turns it back on. A secret survives a deployment.

The Workers free plan allows 10 ms of CPU per request, which is tight for a stream read event by event. The paid plan is advised. Its
bill is not part of the 200 $, so add a Cloudflare rate limiting or WAF rule if the service is attacked.

## Test

```sh
npm test         # rules and accounts
npm run e2e      # the real Worker in the local runtime, against a fake model: no key, no model called
```

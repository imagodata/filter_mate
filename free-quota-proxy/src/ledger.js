// The accounts of the month. One instance serves everything, so a reservation cannot race another one.

const RESERVATION_LIFETIME_MS = 15 * 60 * 1000;
export const REGISTRATIONS_PER_IP_PER_DAY = 3;
export const REGISTRATIONS_PER_DAY = 200; // what ends many addresses at once; 400 tokens would already spend the budget
export const REQUESTS_PER_MINUTE = 30; // a single question can take a dozen calls in a few seconds
export const REQUESTS_PER_DAY = 300;
export const CONCURRENT_REQUESTS = 2;

function monthOf(time) {
  return new Date(time).toISOString().slice(0, 7);
}

function dayOf(time) {
  return new Date(time).toISOString().slice(0, 10);
}

const empty = () => ({ spent: 0, reserved: 0 });

export function validLimits(limits) {
  return [limits.budget, limits.user, limits.ip].every((value) => Number.isFinite(value) && value > 0);
}

export class Ledger {
  /** `limits` are in millionths of a dollar: { budget, user, ip }. `storage` is the storage of a Durable Object. */
  constructor(storage, limits, now = () => Date.now()) {
    this.storage = storage;
    this.limits = limits;
    this.now = now;
  }

  /** A new month starts from nothing, except what is in flight and today's registrations. */
  async rollMonth() {
    const month = monthOf(this.now());
    if ((await this.storage.get("month")) === month) return;
    const flying = await this.storage.list({ prefix: "r:" });
    const registered = await this.storage.list({ prefix: `reg:${dayOf(this.now())}` });
    const dayCount = await this.storage.get(`regs:${dayOf(this.now())}`);
    await this.storage.deleteAll();
    const fresh = { month, ...Object.fromEntries(registered) };
    if (dayCount) fresh[`regs:${dayOf(this.now())}`] = dayCount;
    for (const [key, reservation] of flying) {
      fresh[key] = reservation;
      for (const name of ["total", `u:${reservation.user}`, `i:${reservation.ip}`]) {
        fresh[name] = fresh[name] || empty();
        fresh[name].reserved += reservation.amount;
      }
      fresh[`u:${reservation.user}`].active = (fresh[`u:${reservation.user}`].active || 0) + 1;
    }
    await this.storage.put(fresh);
  }

  async register(ip) {
    await this.rollMonth();
    const day = dayOf(this.now());
    const key = `reg:${day}:${ip}`;
    const count = (await this.storage.get(key)) || 0;
    const all = (await this.storage.get(`regs:${day}`)) || 0;
    if (count >= REGISTRATIONS_PER_IP_PER_DAY || all >= REGISTRATIONS_PER_DAY) return false;
    await this.storage.put({ [key]: count + 1, [`regs:${day}`]: all + 1 });
    return true;
  }

  /** Written together: a crash leaves the reservation whole, or gone with its accounts corrected. */
  async release(key, reservation, amount) {
    const names = ["total", `u:${reservation.user}`, `i:${reservation.ip}`];
    const accounts = await Promise.all(names.map((name) => this.storage.get(name)));
    const changes = {};
    names.forEach((name, index) => {
      const account = accounts[index];
      if (!account) return;
      account.reserved = Math.max(0, account.reserved - reservation.amount);
      account.spent += amount;
      if (name.startsWith("u:")) account.active = Math.max(0, (account.active || 0) - 1);
      changes[name] = account;
    });
    this.storage.delete(key);
    await this.storage.put(changes);
  }

  /** A request that never said how it ended is charged its worst case. */
  async sweep() {
    const limit = this.now() - RESERVATION_LIFETIME_MS;
    for (const [key, reservation] of await this.storage.list({ prefix: "r:" })) {
      if (reservation.at < limit) await this.release(key, reservation, reservation.amount);
    }
  }

  async reserve(userId, ipId, amount) {
    await this.rollMonth();
    await this.sweep();
    const now = this.now();
    const total = (await this.storage.get("total")) || empty();
    const user = (await this.storage.get(`u:${userId}`)) || { ...empty(), active: 0, minute: 0, perMinute: 0, day: "", perDay: 0 };
    const ip = (await this.storage.get(`i:${ipId}`)) || empty();
    // Written as "fits", not "exceeds": a limit or a total that is not a number refuses.
    const fits = (account, limit, withHeld) => account.spent + (withHeld ? account.reserved : 0) + amount <= limit;
    if (!fits(total, this.limits.budget, false)) return { refused: "budget" };
    if (!fits(user, this.limits.user, false) || !fits(ip, this.limits.ip, false)) return { refused: "quota" };
    if (!fits(total, this.limits.budget, true) || !fits(user, this.limits.user, true) || !fits(ip, this.limits.ip, true)) {
      return { refused: "rate" }; // what requests in flight hold will mostly come back
    }
    const minute = Math.floor(now / 60000);
    const day = dayOf(now);
    if (user.minute !== minute) Object.assign(user, { minute, perMinute: 0 });
    if (user.day !== day) Object.assign(user, { day, perDay: 0 });
    if (user.active >= CONCURRENT_REQUESTS || user.perMinute >= REQUESTS_PER_MINUTE || user.perDay >= REQUESTS_PER_DAY) return { refused: "rate" };
    user.active += 1;
    user.perMinute += 1;
    user.perDay += 1;
    for (const account of [total, user, ip]) account.reserved += amount;
    const id = crypto.randomUUID();
    await this.storage.put({ total, [`u:${userId}`]: user, [`i:${ipId}`]: ip, [`r:${id}`]: { user: userId, ip: ipId, amount, at: now } });
    return { id };
  }

  async settle(id, amount) {
    const key = `r:${id}`;
    const reservation = await this.storage.get(key);
    if (!reservation) return; // settled already
    await this.release(key, reservation, Number.isFinite(amount) && amount >= 0 ? amount : reservation.amount);
  }
}

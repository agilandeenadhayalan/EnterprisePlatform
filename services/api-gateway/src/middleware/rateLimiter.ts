import { Request, Response, NextFunction } from "express";
import Redis from "ioredis";
import { config } from "../config";

/**
 * Token-bucket rate limiter backed by Redis.
 *
 * Each client IP gets a bucket with `maxTokens` tokens.
 * Tokens refill at `refillRate` tokens per window.
 * Every request consumes one token. When the bucket is empty the
 * request is rejected with 429 Too Many Requests.
 *
 * All state is stored in Redis so the limiter works across multiple
 * gateway instances.
 */

let redis: Redis | null = null;

function getRedis(): Redis {
  if (!redis) {
    redis = new Redis(config.redis.url, {
      maxRetriesPerRequest: 1,
      lazyConnect: true,
      retryStrategy: (times: number) => {
        if (times > 3) return null; // stop retrying
        return Math.min(times * 200, 2000);
      },
    });
    redis.on("error", (err) => {
      console.error("[RateLimiter] Redis connection error:", err.message);
    });
  }
  return redis;
}

// Lua script executed atomically in Redis via EVALSHA / EVAL.
// Returns [allowed (0|1), remaining tokens, retry-after seconds].
const LUA_TOKEN_BUCKET = `
local key          = KEYS[1]
local max_tokens   = tonumber(ARGV[1])
local refill_rate  = tonumber(ARGV[2])
local window_ms    = tonumber(ARGV[3])
local now          = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens      = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
  tokens      = max_tokens
  last_refill = now
end

-- Refill tokens based on elapsed time
local elapsed   = now - last_refill
local refill    = math.floor(elapsed / window_ms) * refill_rate
if refill > 0 then
  tokens      = math.min(max_tokens, tokens + refill)
  last_refill = now
end

local allowed  = 0
local remaining = tokens

if tokens > 0 then
  allowed   = 1
  remaining = tokens - 1
  redis.call('HMSET', key, 'tokens', remaining, 'last_refill', last_refill)
  redis.call('EXPIRE', key, math.ceil(window_ms / 1000) * 2)
else
  redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
  redis.call('EXPIRE', key, math.ceil(window_ms / 1000) * 2)
end

local retry_after = 0
if allowed == 0 then
  retry_after = math.ceil((window_ms - (now - last_refill)) / 1000)
  if retry_after < 1 then retry_after = 1 end
end

return { allowed, remaining, retry_after }
`;

/**
 * Run the Lua token-bucket script on Redis.
 * Uses the standard ioredis `.call("EVAL", ...)` pattern.
 */
async function runLuaBucket(
  client: Redis,
  key: string
): Promise<[number, number, number]> {
  const result = await client.call(
    "EVAL",
    LUA_TOKEN_BUCKET,
    "1", // number of KEYS
    key,
    String(config.rateLimiter.maxTokens),
    String(config.rateLimiter.refillRate),
    String(config.rateLimiter.windowMs),
    String(Date.now())
  );
  return result as [number, number, number];
}

/**
 * In-memory fallback when Redis is unavailable.
 */
const localBuckets = new Map<
  string,
  { tokens: number; lastRefill: number }
>();

function localTokenBucket(ip: string): {
  allowed: boolean;
  remaining: number;
  retryAfter: number;
} {
  const now = Date.now();
  let bucket = localBuckets.get(ip);

  if (!bucket) {
    bucket = { tokens: config.rateLimiter.maxTokens, lastRefill: now };
    localBuckets.set(ip, bucket);
  }

  // Refill
  const elapsed = now - bucket.lastRefill;
  const refill =
    Math.floor(elapsed / config.rateLimiter.windowMs) *
    config.rateLimiter.refillRate;
  if (refill > 0) {
    bucket.tokens = Math.min(
      config.rateLimiter.maxTokens,
      bucket.tokens + refill
    );
    bucket.lastRefill = now;
  }

  if (bucket.tokens > 0) {
    bucket.tokens -= 1;
    return { allowed: true, remaining: bucket.tokens, retryAfter: 0 };
  }

  const retryAfter = Math.max(
    1,
    Math.ceil(
      (config.rateLimiter.windowMs - (now - bucket.lastRefill)) / 1000
    )
  );
  return { allowed: false, remaining: 0, retryAfter };
}

export { localTokenBucket };

export function rateLimiterMiddleware() {
  return async (req: Request, res: Response, next: NextFunction) => {
    const ip =
      (req.headers["x-forwarded-for"] as string)?.split(",")[0]?.trim() ||
      req.socket.remoteAddress ||
      "unknown";

    const key = `rl:${ip}`;

    try {
      const client = getRedis();
      if (client.status !== "ready") {
        throw new Error("Redis not ready");
      }

      const [allowed, remaining, retryAfter] = await runLuaBucket(client, key);

      res.setHeader("X-RateLimit-Limit", config.rateLimiter.maxTokens);
      res.setHeader("X-RateLimit-Remaining", remaining);

      if (!allowed) {
        res.setHeader("Retry-After", retryAfter);
        res.status(429).json({
          error: "Too Many Requests",
          message: `Rate limit exceeded. Try again in ${retryAfter}s.`,
        });
        return;
      }

      next();
    } catch {
      // Redis unavailable — fall back to in-memory limiter
      const { allowed, remaining, retryAfter } = localTokenBucket(ip);

      res.setHeader("X-RateLimit-Limit", config.rateLimiter.maxTokens);
      res.setHeader("X-RateLimit-Remaining", remaining);

      if (!allowed) {
        res.setHeader("Retry-After", retryAfter);
        res.status(429).json({
          error: "Too Many Requests",
          message: `Rate limit exceeded. Try again in ${retryAfter}s.`,
        });
        return;
      }

      next();
    }
  };
}

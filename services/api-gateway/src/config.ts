import dotenv from "dotenv";

dotenv.config();

export interface ServiceRoute {
  prefix: string;
  target: string;
}

export const config = {
  port: parseInt(process.env.PORT || "8000", 10),

  redis: {
    url: process.env.REDIS_URL || "redis://localhost:6379",
  },

  jwt: {
    secret: process.env.JWT_SECRET || "dev-jwt-secret-change-in-production",
    algorithms: (process.env.JWT_ALGORITHMS || "HS256").split(",") as Array<
      "HS256" | "HS384" | "HS512" | "RS256"
    >,
  },

  rateLimiter: {
    maxTokens: parseInt(process.env.RATE_LIMIT_MAX_TOKENS || "100", 10),
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || "60000", 10),
    refillRate: parseInt(process.env.RATE_LIMIT_REFILL_RATE || "100", 10),
  },

  circuitBreaker: {
    failureThreshold: parseInt(
      process.env.CIRCUIT_BREAKER_FAILURE_THRESHOLD || "5",
      10
    ),
    resetTimeoutMs: parseInt(
      process.env.CIRCUIT_BREAKER_RESET_TIMEOUT_MS || "30000",
      10
    ),
  },
};

/**
 * Backend service route table.
 * Inside Docker the hostnames are the container service names.
 * For local development override with env vars or use localhost + mapped ports.
 */
export const serviceRoutes: ServiceRoute[] = [
  {
    prefix: "/api/v1/auth",
    target: process.env.AUTH_SERVICE_URL || "http://auth-service:8010",
  },
  {
    prefix: "/api/v1/sessions",
    target: process.env.SESSION_SERVICE_URL || "http://session-service:8011",
  },
  {
    prefix: "/api/v1/otp",
    target: process.env.OTP_SERVICE_URL || "http://otp-service:8012",
  },
  {
    prefix: "/api/v1/access",
    target:
      process.env.ACCESS_CONTROL_SERVICE_URL ||
      "http://access-control-service:8013",
  },
  {
    prefix: "/api/v1/devices",
    target: process.env.DEVICE_SERVICE_URL || "http://device-service:8014",
  },
  {
    prefix: "/api/v1/sso",
    target: process.env.SSO_SERVICE_URL || "http://sso-service:8015",
  },
  {
    prefix: "/api/v1/users",
    target: process.env.USER_SERVICE_URL || "http://user-service:8020",
  },
  {
    prefix: "/api/v1/profiles",
    target: process.env.PROFILE_SERVICE_URL || "http://profile-service:8021",
  },
  {
    prefix: "/api/v1/addresses",
    target: process.env.ADDRESS_SERVICE_URL || "http://address-service:8022",
  },
  {
    prefix: "/api/v1/activities",
    target: process.env.ACTIVITY_SERVICE_URL || "http://activity-service:8023",
  },
  {
    prefix: "/api/v1/preferences",
    target:
      process.env.PREFERENCES_SERVICE_URL ||
      "http://preferences-service:8024",
  },
  {
    prefix: "/api/v1/configs",
    target: process.env.CONFIG_SERVICE_URL || "http://config-service:8030",
  },
  {
    prefix: "/api/v1/flags",
    target:
      process.env.FEATURE_FLAG_SERVICE_URL ||
      "http://feature-flag-service:8031",
  },
];

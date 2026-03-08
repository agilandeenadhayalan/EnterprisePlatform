import express from "express";
import cors from "cors";
import { config, serviceRoutes } from "./config";
import { rateLimiterMiddleware } from "./middleware/rateLimiter";
import { authMiddleware } from "./middleware/auth";
import { circuitBreakerMiddleware } from "./middleware/circuitBreaker";
import { createProxyRouter } from "./routes/proxy";

const app = express();

// ---------------------------------------------------------------------------
// Global middleware
// ---------------------------------------------------------------------------
app.use(cors());
app.use(express.json({ limit: "1mb" }));

// ---------------------------------------------------------------------------
// Health endpoint (no auth, no rate-limit)
// ---------------------------------------------------------------------------
app.get("/health", (_req, res) => {
  const services = serviceRoutes.map((r) => {
    const name = r.prefix.split("/").filter(Boolean).pop() || "unknown";
    return { name, target: r.target };
  });

  res.json({
    status: "healthy",
    service: "api-gateway",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    routes: services,
  });
});

// ---------------------------------------------------------------------------
// Rate limiter -> Auth -> Circuit Breaker -> Proxy
// ---------------------------------------------------------------------------
app.use(rateLimiterMiddleware());
app.use(authMiddleware());
app.use(circuitBreakerMiddleware());
app.use(createProxyRouter());

// ---------------------------------------------------------------------------
// 404 catch-all
// ---------------------------------------------------------------------------
app.use((_req, res) => {
  res.status(404).json({
    error: "Not Found",
    message: "No matching route. Check the path and try again.",
  });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
const server = app.listen(config.port, () => {
  console.log(`[api-gateway] listening on port ${config.port}`);
  console.log(
    `[api-gateway] proxying ${serviceRoutes.length} backend services`
  );
});

export { app, server };

import express from "express";
import cors from "cors";
import { config } from "./config";
import meRouter from "./routes/me";
import dashboardRouter from "./routes/dashboard";

const app = express();

// ---------------------------------------------------------------------------
// Global middleware
// ---------------------------------------------------------------------------
app.use(cors());
app.use(express.json({ limit: "1mb" }));

// ---------------------------------------------------------------------------
// Health endpoint
// ---------------------------------------------------------------------------
app.get("/health", (_req, res) => {
  res.json({
    status: "healthy",
    service: "bff-service",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// ---------------------------------------------------------------------------
// Aggregation routes
// ---------------------------------------------------------------------------
app.use("/me", meRouter);
app.use("/dashboard", dashboardRouter);

// ---------------------------------------------------------------------------
// 404 catch-all
// ---------------------------------------------------------------------------
app.use((_req, res) => {
  res.status(404).json({
    error: "Not Found",
    message: "No matching route.",
  });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
const server = app.listen(config.port, () => {
  console.log(`[bff-service] listening on port ${config.port}`);
});

export { app, server };

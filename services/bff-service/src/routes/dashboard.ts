import { Router, Request, Response } from "express";
import axios, { AxiosError } from "axios";
import { config } from "../config";

const router = Router();

/**
 * GET /dashboard
 *
 * Aggregation endpoint that calls three backend services in parallel:
 *   - user-service          -> user data
 *   - activity-service      -> recent activity
 *   - feature-flag-service  -> active flags
 *
 * The Authorization header from the original request is forwarded to
 * every backend call.
 */
router.get("/", async (req: Request, res: Response) => {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    res.status(401).json({
      error: "Unauthorized",
      message: "Missing Authorization header.",
    });
    return;
  }

  const headers = { Authorization: authHeader };
  const timeout = config.requestTimeoutMs;

  try {
    const [userRes, activityRes, flagsRes] = await Promise.allSettled([
      axios.get(`${config.services.userService}/me`, { headers, timeout }),
      axios.get(`${config.services.activityService}/activities/recent`, {
        headers,
        timeout,
      }),
      axios.get(`${config.services.featureFlagService}/flags`, {
        headers,
        timeout,
      }),
    ]);

    const user =
      userRes.status === "fulfilled" ? userRes.value.data : null;
    const recentActivity =
      activityRes.status === "fulfilled" ? activityRes.value.data : [];
    const activeFlags =
      flagsRes.status === "fulfilled" ? flagsRes.value.data : [];

    // Log partial failures
    if (userRes.status === "rejected") {
      const err = userRes.reason as AxiosError;
      console.warn("[bff /dashboard] user-service failed:", err.message);
    }
    if (activityRes.status === "rejected") {
      const err = activityRes.reason as AxiosError;
      console.warn(
        "[bff /dashboard] activity-service failed:",
        err.message
      );
    }
    if (flagsRes.status === "rejected") {
      const err = flagsRes.reason as AxiosError;
      console.warn(
        "[bff /dashboard] feature-flag-service failed:",
        err.message
      );
    }

    if (!user) {
      res.status(502).json({
        error: "Bad Gateway",
        message: "Unable to retrieve user data from user-service.",
      });
      return;
    }

    res.json({ user, recentActivity, activeFlags });
  } catch (err) {
    console.error("[bff /dashboard] unexpected error:", err);
    res.status(500).json({
      error: "Internal Server Error",
      message: "An unexpected error occurred while aggregating dashboard data.",
    });
  }
});

export default router;

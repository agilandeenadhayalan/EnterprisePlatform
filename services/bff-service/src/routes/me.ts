import { Router, Request, Response } from "express";
import axios, { AxiosError } from "axios";
import { config } from "../config";

const router = Router();

/**
 * GET /me
 *
 * Aggregation endpoint that calls three backend services in parallel:
 *   - user-service   -> user data
 *   - profile-service -> profile data
 *   - preferences-service -> user preferences
 *
 * The Authorization header from the original request is forwarded to
 * every backend call so that the services can authenticate the caller.
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
    const [userRes, profileRes, preferencesRes] = await Promise.allSettled([
      axios.get(`${config.services.userService}/me`, { headers, timeout }),
      axios.get(`${config.services.profileService}/profiles/me`, {
        headers,
        timeout,
      }),
      axios.get(`${config.services.preferencesService}/preferences/me`, {
        headers,
        timeout,
      }),
    ]);

    const user =
      userRes.status === "fulfilled" ? userRes.value.data : null;
    const profile =
      profileRes.status === "fulfilled" ? profileRes.value.data : null;
    const preferences =
      preferencesRes.status === "fulfilled"
        ? preferencesRes.value.data
        : [];

    // Log partial failures for observability
    if (userRes.status === "rejected") {
      const err = userRes.reason as AxiosError;
      console.warn("[bff /me] user-service failed:", err.message);
    }
    if (profileRes.status === "rejected") {
      const err = profileRes.reason as AxiosError;
      console.warn("[bff /me] profile-service failed:", err.message);
    }
    if (preferencesRes.status === "rejected") {
      const err = preferencesRes.reason as AxiosError;
      console.warn("[bff /me] preferences-service failed:", err.message);
    }

    // If the user-service itself is down the aggregation is meaningless
    if (!user) {
      res.status(502).json({
        error: "Bad Gateway",
        message: "Unable to retrieve user data from user-service.",
      });
      return;
    }

    res.json({ user, profile, preferences });
  } catch (err) {
    console.error("[bff /me] unexpected error:", err);
    res.status(500).json({
      error: "Internal Server Error",
      message: "An unexpected error occurred while aggregating data.",
    });
  }
});

export default router;

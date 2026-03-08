import dotenv from "dotenv";

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || "8002", 10),

  /** Backend service base URLs (Docker hostnames by default). */
  services: {
    userService:
      process.env.USER_SERVICE_URL || "http://user-service:8020",
    profileService:
      process.env.PROFILE_SERVICE_URL || "http://profile-service:8021",
    preferencesService:
      process.env.PREFERENCES_SERVICE_URL || "http://preferences-service:8024",
    activityService:
      process.env.ACTIVITY_SERVICE_URL || "http://activity-service:8023",
    featureFlagService:
      process.env.FEATURE_FLAG_SERVICE_URL || "http://feature-flag-service:8031",
  },

  /** Request timeout in milliseconds for backend calls. */
  requestTimeoutMs: parseInt(process.env.REQUEST_TIMEOUT_MS || "5000", 10),
};

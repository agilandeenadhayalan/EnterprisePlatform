import dotenv from "dotenv";

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || "8001", 10),

  /** Backend service base URLs (Docker hostnames by default). */
  services: {
    userService:
      process.env.USER_SERVICE_URL || "http://user-service:8020",
    profileService:
      process.env.PROFILE_SERVICE_URL || "http://profile-service:8021",
    addressService:
      process.env.ADDRESS_SERVICE_URL || "http://address-service:8022",
    activityService:
      process.env.ACTIVITY_SERVICE_URL || "http://activity-service:8023",
    preferencesService:
      process.env.PREFERENCES_SERVICE_URL || "http://preferences-service:8024",
    sessionService:
      process.env.SESSION_SERVICE_URL || "http://session-service:8011",
    featureFlagService:
      process.env.FEATURE_FLAG_SERVICE_URL || "http://feature-flag-service:8031",
    authService:
      process.env.AUTH_SERVICE_URL || "http://auth-service:8010",
  },
};

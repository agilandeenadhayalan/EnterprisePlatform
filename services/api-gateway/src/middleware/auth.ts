import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { config } from "../config";

/**
 * Paths that do NOT require a valid JWT.
 */
const PUBLIC_PATHS = [
  "/health",
  "/api/v1/auth/register",
  "/api/v1/auth/login",
];

function isPublicPath(path: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => path === p || path.startsWith(p + "/") || path.startsWith(p + "?")
  );
}

export interface AuthenticatedRequest extends Request {
  user?: jwt.JwtPayload;
}

/**
 * JWT validation middleware.
 *
 * - Skips validation for public paths (health, register, login).
 * - Expects the token in the `Authorization: Bearer <token>` header.
 * - On success attaches the decoded payload to `req.user`.
 * - On failure responds with 401.
 */
export function authMiddleware() {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (isPublicPath(req.path)) {
      return next();
    }

    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      res.status(401).json({
        error: "Unauthorized",
        message: "Missing or malformed Authorization header.",
      });
      return;
    }

    const token = authHeader.slice(7); // strip "Bearer "

    try {
      const decoded = jwt.verify(token, config.jwt.secret, {
        algorithms: config.jwt.algorithms,
      });
      req.user = decoded as jwt.JwtPayload;
      next();
    } catch (err) {
      const message =
        err instanceof jwt.TokenExpiredError
          ? "Token has expired."
          : "Invalid token.";
      res.status(401).json({ error: "Unauthorized", message });
    }
  };
}

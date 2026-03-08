import { Router, Request, Response } from "express";
import {
  createProxyMiddleware,
  Options,
  responseInterceptor,
} from "http-proxy-middleware";
import { serviceRoutes } from "../config";
import { recordSuccess, recordFailure } from "../middleware/circuitBreaker";

/**
 * Derive a short service name from the route prefix.
 * e.g. "/api/v1/users" => "users"
 */
function serviceNameFromPrefix(prefix: string): string {
  const parts = prefix.split("/").filter(Boolean);
  return parts[parts.length - 1] || "unknown";
}

/**
 * Build an Express router that mounts an http-proxy-middleware instance
 * for every entry in the service routes table.
 */
export function createProxyRouter(): Router {
  const router = Router();

  for (const route of serviceRoutes) {
    const serviceName = serviceNameFromPrefix(route.prefix);

    const proxyOptions: Options = {
      target: route.target,
      changeOrigin: true,
      pathRewrite: {
        [`^${route.prefix}`]: "", // strip the gateway prefix
      },
      // Self-handle the response so we can track success / failure for
      // the circuit breaker without interfering with the body.
      selfHandleResponse: true,
      on: {
        proxyRes: responseInterceptor(
          async (responseBuffer, proxyRes, _req, _res) => {
            const statusCode = proxyRes.statusCode ?? 500;
            if (statusCode >= 500) {
              recordFailure(serviceName);
            } else {
              recordSuccess(serviceName);
            }
            return responseBuffer;
          }
        ),
        error: (_err, _req, res) => {
          recordFailure(serviceName);
          // Avoid double-sending if headers are already sent
          if (res && "headersSent" in res && !(res as Response).headersSent) {
            (res as Response).status(502).json({
              error: "Bad Gateway",
              message: `Upstream service '${serviceName}' is unreachable.`,
            });
          }
        },
      },
      // Forward original host header
      headers: {
        "X-Forwarded-By": "api-gateway",
      },
    };

    router.use(route.prefix, createProxyMiddleware(proxyOptions));
  }

  return router;
}

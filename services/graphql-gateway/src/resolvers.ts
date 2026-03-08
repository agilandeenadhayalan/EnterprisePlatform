import axios, { AxiosError } from "axios";
import { config } from "./config";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface GqlContext {
  authHeader?: string;
}

/**
 * Convenience wrapper around axios.get that forwards the Authorization
 * header from the original GraphQL request to the backend service.
 */
async function serviceGet<T = unknown>(
  url: string,
  ctx: GqlContext
): Promise<T | null> {
  try {
    const headers: Record<string, string> = {};
    if (ctx.authHeader) {
      headers["Authorization"] = ctx.authHeader;
    }
    const res = await axios.get<T>(url, { headers, timeout: 5000 });
    return res.data;
  } catch (err) {
    const axErr = err as AxiosError;
    if (axErr.response?.status === 404) return null;
    console.error(`[graphql-gateway] GET ${url} failed:`, axErr.message);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Resolvers
// ---------------------------------------------------------------------------

export const resolvers = {
  Query: {
    /**
     * `me` — fetch the current user from user-service.
     * The user ID is typically embedded in the JWT.  Here we call a
     * `/me` endpoint on the user-service which resolves it from the
     * forwarded token.
     */
    me: async (
      _parent: unknown,
      _args: unknown,
      ctx: GqlContext
    ) => {
      return serviceGet(
        `${config.services.userService}/me`,
        ctx
      );
    },

    /**
     * `user(id)` — look up a single user by ID.
     */
    user: async (
      _parent: unknown,
      args: { id: string },
      ctx: GqlContext
    ) => {
      return serviceGet(
        `${config.services.userService}/users/${args.id}`,
        ctx
      );
    },

    /**
     * `users(limit, cursor)` — paginated user list.
     */
    users: async (
      _parent: unknown,
      args: { limit?: number; cursor?: string },
      ctx: GqlContext
    ) => {
      const params = new URLSearchParams();
      if (args.limit) params.set("limit", String(args.limit));
      if (args.cursor) params.set("cursor", args.cursor);

      const qs = params.toString();
      const url = `${config.services.userService}/users${qs ? "?" + qs : ""}`;

      interface UsersResponse {
        items?: Array<Record<string, unknown>>;
        next_cursor?: string;
      }

      const data = await serviceGet<UsersResponse>(url, ctx);
      if (!data) {
        return { edges: [], pageInfo: { hasNextPage: false, endCursor: null } };
      }

      const items = data.items || [];
      const edges = items.map((u: Record<string, unknown>) => ({
        node: u,
        cursor: u.id as string,
      }));

      return {
        edges,
        pageInfo: {
          hasNextPage: !!data.next_cursor,
          endCursor: data.next_cursor || null,
        },
      };
    },

    /**
     * `flags` — list all feature flags.
     */
    flags: async (
      _parent: unknown,
      _args: unknown,
      ctx: GqlContext
    ) => {
      const data = await serviceGet<Array<Record<string, unknown>>>(
        `${config.services.featureFlagService}/flags`,
        ctx
      );
      return data || [];
    },

    /**
     * `evaluateFlag(name)` — evaluate a single flag.
     */
    evaluateFlag: async (
      _parent: unknown,
      args: { name: string },
      ctx: GqlContext
    ) => {
      return serviceGet(
        `${config.services.featureFlagService}/flags/${encodeURIComponent(args.name)}/evaluate`,
        ctx
      );
    },
  },

  // -----------------------------------------------------------------------
  // Field-level resolvers  (lazy loading related entities)
  // -----------------------------------------------------------------------

  User: {
    profile: async (
      parent: { id: string },
      _args: unknown,
      ctx: GqlContext
    ) => {
      return serviceGet(
        `${config.services.profileService}/profiles/${parent.id}`,
        ctx
      );
    },

    addresses: async (
      parent: { id: string },
      _args: unknown,
      ctx: GqlContext
    ) => {
      const data = await serviceGet<Array<Record<string, unknown>>>(
        `${config.services.addressService}/addresses?user_id=${parent.id}`,
        ctx
      );
      return data || [];
    },

    preferences: async (
      parent: { id: string },
      _args: unknown,
      ctx: GqlContext
    ) => {
      const data = await serviceGet<Array<Record<string, unknown>>>(
        `${config.services.preferencesService}/preferences?user_id=${parent.id}`,
        ctx
      );
      return data || [];
    },

    sessions: async (
      parent: { id: string },
      _args: unknown,
      ctx: GqlContext
    ) => {
      const data = await serviceGet<Array<Record<string, unknown>>>(
        `${config.services.sessionService}/sessions?user_id=${parent.id}`,
        ctx
      );
      return data || [];
    },
  },
};

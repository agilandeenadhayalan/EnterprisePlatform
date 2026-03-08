import express from "express";
import cors from "cors";
import { ApolloServer } from "@apollo/server";
import { expressMiddleware } from "@apollo/server/express4";
import { config } from "./config";
import { typeDefs } from "./schema";
import { resolvers } from "./resolvers";

interface GqlContext {
  authHeader?: string;
}

async function main() {
  const app = express();

  // ------------------------------------------------------------------
  // Apollo Server
  // ------------------------------------------------------------------
  const apollo = new ApolloServer<GqlContext>({
    typeDefs,
    resolvers,
    introspection: true,
  });

  await apollo.start();

  // ------------------------------------------------------------------
  // Global middleware
  // ------------------------------------------------------------------
  app.use(cors());
  app.use(express.json({ limit: "1mb" }));

  // ------------------------------------------------------------------
  // Health endpoint
  // ------------------------------------------------------------------
  app.get("/health", (_req, res) => {
    res.json({
      status: "healthy",
      service: "graphql-gateway",
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    });
  });

  // ------------------------------------------------------------------
  // GraphQL endpoint
  // ------------------------------------------------------------------
  app.use(
    "/graphql",
    expressMiddleware(apollo, {
      context: async ({ req }) => {
        // Forward the Authorization header so resolvers can pass it to
        // backend services.
        return {
          authHeader: req.headers.authorization,
        };
      },
    })
  );

  // ------------------------------------------------------------------
  // Start
  // ------------------------------------------------------------------
  app.listen(config.port, () => {
    console.log(
      `[graphql-gateway] listening on port ${config.port}`
    );
    console.log(
      `[graphql-gateway] GraphQL endpoint: http://localhost:${config.port}/graphql`
    );
  });
}

main().catch((err) => {
  console.error("[graphql-gateway] Fatal startup error:", err);
  process.exit(1);
});

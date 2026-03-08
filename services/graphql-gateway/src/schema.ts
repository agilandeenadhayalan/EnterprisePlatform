/**
 * GraphQL SDL type definitions for the Smart Mobility Platform unified graph.
 */

export const typeDefs = `#graphql
  type Query {
    "The currently authenticated user (resolved from the JWT subject)."
    me: User

    "Look up a user by ID."
    user(id: ID!): User

    "Paginated list of users. Returns a connection with cursor-based pagination."
    users(limit: Int, cursor: String): UserConnection

    "All feature flags."
    flags: [FeatureFlag]

    "Evaluate a single feature flag by name."
    evaluateFlag(name: String!): FlagEvaluation
  }

  # -------------------------------------------------------------------
  # User & related types
  # -------------------------------------------------------------------

  type User {
    id: ID!
    email: String!
    fullName: String!
    role: String!
    createdAt: String
    updatedAt: String

    "User's profile (lazy-loaded from profile-service)."
    profile: Profile

    "Addresses on file (lazy-loaded from address-service)."
    addresses: [Address]

    "User preferences (lazy-loaded from preferences-service)."
    preferences: [Preference]

    "Active sessions (lazy-loaded from session-service)."
    sessions: [Session]
  }

  type UserConnection {
    edges: [UserEdge]
    pageInfo: PageInfo
  }

  type UserEdge {
    node: User
    cursor: String
  }

  type PageInfo {
    hasNextPage: Boolean!
    endCursor: String
  }

  # -------------------------------------------------------------------
  # Profile
  # -------------------------------------------------------------------

  type Profile {
    id: ID
    userId: String
    displayName: String
    avatarUrl: String
    bio: String
    phone: String
  }

  # -------------------------------------------------------------------
  # Address
  # -------------------------------------------------------------------

  type Address {
    id: ID
    userId: String
    label: String
    line1: String
    line2: String
    city: String
    state: String
    postalCode: String
    country: String
  }

  # -------------------------------------------------------------------
  # Preference
  # -------------------------------------------------------------------

  type Preference {
    id: ID
    userId: String
    key: String
    value: String
  }

  # -------------------------------------------------------------------
  # Session
  # -------------------------------------------------------------------

  type Session {
    id: ID
    userId: String
    deviceInfo: String
    ipAddress: String
    createdAt: String
    expiresAt: String
  }

  # -------------------------------------------------------------------
  # Feature Flags
  # -------------------------------------------------------------------

  type FeatureFlag {
    name: String!
    enabled: Boolean!
    description: String
    rules: String
  }

  type FlagEvaluation {
    name: String!
    enabled: Boolean!
    variant: String
  }
`;

import { betterAuth } from "better-auth";
import { z } from "zod";

import { investorPersonas } from "../data/investor-personas";
import { authPool } from "./db";

const secret = process.env.BETTER_AUTH_SECRET;
const baseURL = process.env.BETTER_AUTH_URL;

if (!secret || secret.length < 32) {
  throw new Error("BETTER_AUTH_SECRET must contain at least 32 characters. Generate a random secret for this app.");
}
if (!baseURL) {
  throw new Error("BETTER_AUTH_URL must be configured with this app's origin.");
}

export const auth = betterAuth({
  database: authPool,
  baseURL,
  secret,
  user: {
    additionalFields: {
      investorPersona: {
        type: "string",
        fieldName: "investor_persona",
        required: false,
        validator: { input: z.enum(investorPersonas.map(({ id }) => id)) },
      },
    },
  },
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
  },
  session: {
    expiresIn: 60 * 60 * 24 * 30,
    updateAge: 60 * 60 * 24,
  },
  rateLimit: {
    enabled: true,
    storage: "database",
  },
});

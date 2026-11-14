import { Pool } from "pg";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing ${name}. Configure the server environment using .env.example.`);
  }
  return value;
}

const globalForDb = globalThis as typeof globalThis & { authPool?: Pool };

export const authPool =
  globalForDb.authPool ??
  new Pool({
    host: requiredEnv("DATABASE_HOST"),
    port: Number(process.env.DATABASE_PORT ?? 5432),
    database: requiredEnv("DATABASE_NAME"),
    user: requiredEnv("DATABASE_USER"),
    password: requiredEnv("DATABASE_PASSWORD"),
    ssl: {
      ca: requiredEnv("DATABASE_CA_CERT").replace(/\\n/g, "\n"),
      rejectUnauthorized: true,
    },
    max: 5,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 10_000,
  });

// Reuse the pool during Next.js development reloads.
if (!globalForDb.authPool) {
  authPool.on("error", () => {
    console.error("An idle authentication database connection failed.");
  });
  globalForDb.authPool = authPool;
}

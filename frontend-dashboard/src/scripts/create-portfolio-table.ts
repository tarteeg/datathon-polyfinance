import { authPool } from "../lib/db";

async function migrate() {
  try {
    await authPool.query(`
      CREATE TABLE IF NOT EXISTS portfolio_holdings (
        user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        ticker TEXT NOT NULL,
        quantity NUMERIC CHECK (quantity > 0),
        PRIMARY KEY (user_id, ticker)
      )
    `);
    console.log("Portfolio table is ready.");
  } finally {
    await authPool.end();
  }
}

migrate().catch((error: Error) => {
  console.error("Portfolio migration failed:", error.name);
  process.exitCode = 1;
});

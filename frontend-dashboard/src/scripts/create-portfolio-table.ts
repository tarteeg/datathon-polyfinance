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
    await authPool.query(`
      CREATE TABLE IF NOT EXISTS headline_impact_cache (
        user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        article_key UUID NOT NULL,
        input_hash TEXT NOT NULL,
        analysis JSONB NOT NULL,
        PRIMARY KEY (user_id, article_key)
      )
    `);
    console.log("Portfolio and headline analysis tables are ready.");
  } finally {
    await authPool.end();
  }
}

migrate().catch((error: Error) => {
  console.error("Portfolio migration failed:", error.name);
  process.exitCode = 1;
});

import { authPool } from "../lib/db";

async function main() {
  // Verify Better Auth's user table exists
  const check = await authPool.query(
    `SELECT to_regclass('"user"') AS user_table`
  );

  if (!check.rows[0]?.user_table) {
    throw new Error(
      'The Better Auth "user" table was not found.'
    );
  }

  await authPool.query(`
    CREATE TABLE IF NOT EXISTS investor_profiles (
      user_id TEXT PRIMARY KEY
        REFERENCES "user"(id) ON DELETE CASCADE,

      investor_data JSONB NOT NULL,

      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);

  console.log("Investor profiles table is ready.");
}

main()
  .catch((error) => {
    console.error("Database migration failed:", error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await authPool.end();
  });

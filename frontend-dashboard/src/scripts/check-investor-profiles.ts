import { authPool } from "../lib/db";

async function main() {
  const result = await authPool.query(`
    SELECT user_id, investor_data, updated_at
    FROM investor_profiles
  `);

  console.log(JSON.stringify(result.rows, null, 2));
}

main()
  .catch(console.error)
  .finally(() => authPool.end());

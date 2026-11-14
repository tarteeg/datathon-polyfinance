import { authPool } from "../lib/db";

async function migrate() {
  const client = await authPool.connect();
  try {
    await client.query("BEGIN");
    await client.query(`
      CREATE TABLE IF NOT EXISTS chat_turns (
        user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        thread_id UUID NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        turn INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        PRIMARY KEY (user_id, thread_id, turn)
      )
    `);
    await client.query("LOCK TABLE chat_turns IN ACCESS EXCLUSIVE MODE");
    const legacy = await client.query(`
      SELECT 1 FROM pg_attribute WHERE attrelid = 'chat_turns'::regclass
        AND attname = 'thread_id' AND NOT attisdropped
    `);
    if (!legacy.rowCount) {
      await client.query(`
        ALTER TABLE chat_turns ADD COLUMN thread_id UUID, ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now();
        WITH owners AS MATERIALIZED (
          SELECT user_id, gen_random_uuid() AS id FROM chat_turns GROUP BY user_id
        )
        UPDATE chat_turns SET thread_id = owners.id FROM owners WHERE chat_turns.user_id = owners.user_id;
        ALTER TABLE chat_turns ALTER COLUMN thread_id SET NOT NULL, DROP CONSTRAINT chat_turns_pkey,
          ADD PRIMARY KEY (user_id, thread_id, turn);
      `);
    }
    await client.query("ALTER TABLE chat_turns ADD COLUMN IF NOT EXISTS chart_snapshot JSONB");
    await client.query("ALTER TABLE chat_turns ADD COLUMN IF NOT EXISTS news_snapshot JSONB");
    await client.query("ALTER TABLE chat_turns ADD COLUMN IF NOT EXISTS stock_snapshot JSONB");
    await client.query("ALTER TABLE chat_turns ADD COLUMN IF NOT EXISTS tool_activity JSONB");
    await client.query("ALTER TABLE chat_turns ADD COLUMN IF NOT EXISTS portfolio_snapshot JSONB");
    await client.query("COMMIT");
    console.log("Chat threads are ready.");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
    await authPool.end();
  }
}

migrate().catch((error: Error) => {
  console.error("Chat migration failed:", error.message);
  process.exitCode = 1;
});

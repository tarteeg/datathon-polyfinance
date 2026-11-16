import { auth } from "@/lib/auth";
import { authPool } from "@/lib/db";

import {
  assembleInvestorRecord,
  investorSubmissionSchema,
} from "@/lib/investor-schema";

export const runtime = "nodejs";

export async function POST(request: Request) {

  let session;

  try {
    session = await auth.api.getSession({
      headers: request.headers,
    });
  } catch (error) {
    console.error("Authentication error:", error);

    return Response.json(
      { error: "Authentication service unavailable." },
      { status: 500 }
    );
  }

  if (!session) {
    return Response.json(
      { error: "Please sign in." },
      { status: 401 }
    );
  }

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return Response.json(
      { error: "Invalid JSON request." },
      { status: 400 }
    );
  }

  const parsed = investorSubmissionSchema.safeParse(body);

  if (!parsed.success) {
    return Response.json(
      {
        error: "Invalid investor data.",
        details: parsed.error.issues.map(issue => ({
          path: issue.path.join("."),
          message: issue.message,
        })),
      },
      { status: 400 }
    );
  }

  const investor = assembleInvestorRecord(
    session.user.id,
    session.user.name,
    parsed.data
  );

  try {
    await authPool.query(
      `
      INSERT INTO investor_profiles (
        user_id,
        investor_data
      )
      VALUES ($1, $2::jsonb)

      ON CONFLICT (user_id)
      DO UPDATE SET
        investor_data = EXCLUDED.investor_data,
        updated_at = NOW()
      `,
      [
        session.user.id,
        JSON.stringify(investor),
      ]
    );

  } catch (error) {
    console.error("Unable to save investor profile:", error);

    return Response.json(
      { error: "Failed to save investor profile." },
      { status: 500 }
    );
  }

  return Response.json({
    success: true,
    investor,
  });
}

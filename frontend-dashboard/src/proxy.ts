import { type NextRequest, NextResponse } from "next/server";

import { auth } from "@/lib/auth";

export async function proxy(request: NextRequest) {
  const session = await auth.api.getSession({
    headers: request.headers,
    query: { disableRefresh: true },
  });

  if (!session) {
    return NextResponse.redirect(new URL("/auth/v1/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/chat/:path*", "/mail/:path*"],
};

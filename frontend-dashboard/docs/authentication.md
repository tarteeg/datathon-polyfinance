# Authentication

The V1 forms use Better Auth with Aurora PostgreSQL through a shared `pg` pool. Authentication stays inside the Next.js app at `/api/auth/*`; there is no separate auth service or ORM.

## Local setup

1. Install dependencies with `npm install`.
2. Copy `.env.example` to `.env.local` if a local file does not already exist. Environment files are ignored by Git.
3. Set `BETTER_AUTH_URL` to the app's exact origin (locally `http://localhost:3000`). Generate `BETTER_AUTH_SECRET` with `openssl rand -base64 32`. Keep the same secret across restarts and instances of the same deployment.
4. Set `DATABASE_HOST` to Aurora's writer endpoint, `DATABASE_PORT` to `5432`, and fill in `DATABASE_NAME`, `DATABASE_USER`, and `DATABASE_PASSWORD`. Use separate variables, not a connection URL; special characters in passwords do not need URL encoding. Quote values containing `#` in the environment file. The database must already exist; the cluster identifier is not the database name. Use a dedicated application database to avoid collisions with existing tables.
5. Obtain the [official AWS RDS CA bundle](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem). Set `DATABASE_CA_CERT` to its PEM content, enclosed in double quotes across multiple lines (or with literal `\n` separators). The app always verifies the TLS certificate and hostname; it never disables certificate verification.
6. Ensure the database security group permits port 5432 from your machine's public IP. Public accessibility alone does not grant access. Use restricted source IPs, not an internet-wide rule.
7. After choosing the intended database, run `npm run auth:generate` to produce SQL for review, or `npm run auth:migrate` to interactively apply Better Auth's schema. Both commands use the installed, pinned CLI and read the local configuration. Generation with this adapter also requires database connectivity. Do not automatically run migrations on app startup or on every deployment.
8. Run `npm run dev`, then open `/auth/v1/register`.

The current local `.env.local` may already contain a generated secret and the AWS CA bundle. Fill in its blank database fields without replacing those values.

The migration creates Better Auth's user, account, session, verification, and database-backed rate-limit tables. It does not create the PostgreSQL database or AWS infrastructure. Use a dedicated, appropriately scoped application database role for deployment rather than the Aurora master login.

## Application behavior

- Registration collects name, email, password, and password confirmation. Passwords must be 8–128 characters; Better Auth handles hashing and credential validation.
- Successful registration or login opens `/dashboard/home`.
- Remembered sessions expire after 30 days; login with Remember me unchecked uses a browser-session cookie.
- `/dashboard/*`, `/chat/*`, and `/mail/*` are checked in the Next.js proxy against the actual session, not just the presence of a cookie. The dashboard also loads the user through `requireSession()`.
- The sidebar displays the signed-in user's name, email, and avatar and has a working logout action.
- Session checks in server rendering/proxy do not refresh cookies. Better Auth's client session endpoint can refresh sessions through normal API requests.
- Google sign-in remains disabled until configured. Email verification and password-reset delivery are not implemented; registrations currently allow unverified email addresses.

## Adding protected features

Use the server-only `getSession()` or `requireSession()` from `src/lib/session.ts` at each protected data or Server Action boundary. Layout redirects and proxy coverage are not substitutes for authorization in an API.

For a new Route Handler, use `getSession()` and return a JSON `401` response when absent. Check resource ownership/roles before reading or mutating application data. Never import `src/lib/auth.ts` or `src/lib/db.ts` in Client Components; clients use `src/lib/auth-client.ts`.

The existing dashboard pages still contain template/demo data. Authentication does not turn the Users/Roles demos into an administration system or add authorization to future endpoints.

## Deployment

Set the exact HTTPS app origin and server-only environment values in the deployment's runtime configuration. Do not prefix credentials with `NEXT_PUBLIC_`. Every server process has a pool limited to five connections; account for the number of instances when sizing Aurora connections.

Amplify deployment is not configured by this change. The template is on Next.js 16; the [Amplify Hosting support matrix](https://docs.aws.amazon.com/amplify/latest/userguide/ssr-amplify-support.html) reviewed for this integration lists support through Next.js 15. Also resolve trusted database network access from the deployed runtime. Do not open Aurora to all IPs to bypass that decision.

Amplify build variables are not automatically SSR runtime variables. Follow [AWS runtime environment guidance](https://docs.aws.amazon.com/amplify/latest/userguide/ssr-environment-variables.html); AWS recommends IAM-based access to secrets rather than baking credentials into deployment artifacts. A production secrets-loading strategy is still required for Amplify. Changing the database to public does not resolve these deployment constraints.

## Verification status

Dependencies and code are prepared. No live database migration, authentication flow, build, lint, or browser validation has been performed. Repository instructions require explicit authorization for validation commands. Once configured, verify registration, invalid/valid login, remembered sessions, reload, logout, expired/revoked sessions, nested route protection, and unavailable-database behavior.

References: [Better Auth PostgreSQL](https://better-auth.com/docs/adapters/postgresql), [Next.js integration](https://better-auth.com/docs/integrations/next), [schema CLI](https://better-auth.com/docs/concepts/cli).

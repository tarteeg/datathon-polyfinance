# syntax=docker/dockerfile:1
FROM node:24-slim AS base
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

FROM base AS deps
# HUSKY=0 skips the "prepare" script (git hooks), which needs a .git directory.
ENV HUSKY=0
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# No secrets are needed at build time. src/lib/db.ts checks its variables when
# the module is imported, so `next build` needs placeholder values. They are set
# for this command only: they are not stored in the image or used at runtime.
# The real DATABASE_*, BETTER_AUTH_* and BACKEND_API_URL values come from the
# environment when the server starts.
RUN DATABASE_HOST=build-placeholder \
    DATABASE_PORT=5432 \
    DATABASE_NAME=build-placeholder \
    DATABASE_USER=build-placeholder \
    DATABASE_PASSWORD=build-placeholder \
    DATABASE_CA_CERT=build-placeholder \
    BETTER_AUTH_SECRET=build-placeholder-build-placeholder-0000 \
    BETTER_AUTH_URL=http://localhost:3000 \
    npm run build \
    && npm prune --omit=dev --ignore-scripts

FROM base AS runner
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/next.config.mjs ./next.config.mjs
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
USER node
EXPOSE 3000
CMD ["node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]

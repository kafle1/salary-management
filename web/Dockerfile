FROM node:22-alpine AS deps
WORKDIR /srv
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /srv
COPY --from=deps /srv/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /srv
ENV NODE_ENV=production
# output: "standalone" traces the files actually imported, so no node_modules copy
COPY --from=builder /srv/.next/standalone ./
COPY --from=builder /srv/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]

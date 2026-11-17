FROM node:20-alpine AS builder

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmjs.org
ARG NPM_TOKEN=

COPY package*.json ./
RUN set -eux; \
    npm config set registry "${NPM_REGISTRY}"; \
    if [ -n "${NPM_TOKEN}" ]; then \
      REG_HOST="$(echo "${NPM_REGISTRY}" | sed -E 's#^https?://##; s#/$##')"; \
      npm config set "//${REG_HOST}/:_authToken" "${NPM_TOKEN}"; \
    fi; \
    if [ -f package-lock.json ]; then npm ci; else npm install; fi; \
    rm -f /root/.npmrc

COPY . .

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]

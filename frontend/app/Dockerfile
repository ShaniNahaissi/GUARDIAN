# Use the official Node.js image for building
FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_BACKEND_URL=https://localhost:8000/api
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# --- Production Stage ---
# Serve with lightweight nginx
FROM nginx:alpine AS production

# Install openssl and generate a self-signed certificate
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx-selfsigned.key \
    -out /etc/nginx/ssl/nginx-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]

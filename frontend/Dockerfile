# Stage 1: Build the Astro site
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build
# Add a log to see what's in the dist directory after build
RUN ls -la dist/

# Stage 2: Serve the static files
FROM node:18-alpine

RUN npm install -g serve

# Be explicit about the directory structure
WORKDIR /app
COPY --from=builder /app/dist ./dist

# Add a log to verify files are copied
RUN ls -la dist/

EXPOSE 3000

# Modified serve command with explicit path and single page application flag
CMD ["serve", "-s", "/app/dist", "-l", "3000", "--single"]
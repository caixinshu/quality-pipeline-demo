FROM mcr.microsoft.com/playwright:v1.48.0-jammy

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY tests/ ./tests/
COPY playwright.config.ts ./

CMD ["npx", "playwright", "test"]

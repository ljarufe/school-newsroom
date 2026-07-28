FROM mcr.microsoft.com/playwright:v1.61.1-noble

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /tests

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

WORKDIR /tests/repository

CMD ["/tests/node_modules/.bin/playwright", "test"]

FROM mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /tests

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

WORKDIR /tests/repository

CMD ["/tests/node_modules/.bin/playwright", "test"]

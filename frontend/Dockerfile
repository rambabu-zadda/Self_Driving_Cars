FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
ARG REACT_APP_BACKEND=http://localhost:8000
ARG REACT_APP_WS_URL=ws://localhost:8000/ws
ENV REACT_APP_BACKEND=$REACT_APP_BACKEND
ENV REACT_APP_WS_URL=$REACT_APP_WS_URL
RUN npm run build

FROM node:20-alpine

WORKDIR /app
COPY --from=build /app/build ./build
COPY server.js ./server.js

EXPOSE 3000
CMD ["node", "server.js"]

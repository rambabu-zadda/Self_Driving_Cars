const http = require("http");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "build");
const port = Number(process.env.PORT || 3000);
const host = "0.0.0.0";

const contentTypes = {
  ".css": "text/css",
  ".html": "text/html",
  ".js": "text/javascript",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain",
};

function sendFile(res, filePath) {
  fs.readFile(filePath, (error, data) => {
    if (error) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, {
      "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream",
    });
    res.end(data);
  });
}

http
  .createServer((req, res) => {
    const urlPath = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    const requested = path.normalize(path.join(root, urlPath));

    if (!requested.startsWith(root)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.stat(requested, (error, stat) => {
      if (!error && stat.isFile()) {
        sendFile(res, requested);
        return;
      }
      sendFile(res, path.join(root, "index.html"));
    });
  })
  .listen(port, host, () => {
    console.log(`Frontend listening on ${host}:${port}`);
  });

import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// If you still need EJS views, keep these lines:
// app.set("view engine", "ejs");
// app.set("views", path.join(__dirname, "views"));
// app.engine("ejs", ejsMate);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Backend proxy configuration
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

// Forward /api/v1 requests to backend (port 8000) to avoid CORS issues
app.use("/api/v1", async (req, res) => {
  const targetUrl = `${BACKEND_URL}${req.originalUrl}`;
  try {
    const fetchOptions = {
      method: req.method,
      headers: {
        "content-type": req.headers["content-type"] || "application/json",
        "accept": "application/json",
        ...(req.headers["authorization"] ? { "authorization": req.headers["authorization"] } : {}),
      },
    };
    if (["POST", "PUT", "PATCH"].includes(req.method) && req.body && Object.keys(req.body).length > 0) {
      fetchOptions.body = JSON.stringify(req.body);
    }

    const backendRes = await fetch(targetUrl, fetchOptions);
    const data = await backendRes.text();
    res.status(backendRes.status);
    const contentType = backendRes.headers.get("content-type");
    if (contentType) res.setHeader("content-type", contentType);
    res.send(data);
  } catch (err) {
    console.error(`[API Proxy Error] ${req.method} ${targetUrl}:`, err.message);
    res.status(502).json({
      error: "Bad Gateway",
      message: `Failed to communicate with backend at ${BACKEND_URL}. Ensure FastAPI backend is running on port 8000.`,
      detail: err.message,
    });
  }
});

// Serve React build instead of /public
app.use(express.static(path.join(__dirname, "frontend")));

// Catch-all route: send React index.html
app.get(/.*/, (req, res) => {
  res.sendFile(path.join(__dirname, "frontend", "index.html"));
});

app.listen(8050, () => {
  console.log("Website is listening at 8050");
  console.log(`API Proxy configured: /api/v1 -> ${BACKEND_URL}/api/v1`);
});


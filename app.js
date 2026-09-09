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

app.use(express.urlencoded({ extended: true }));

// Serve React build instead of /public
app.use(express.static(path.join(__dirname, "frontend")));

// Catch-all route: send React index.html
app.get(/.*/, (req, res) => {
  res.sendFile(path.join(__dirname, "frontend", "index.html"));
});


app.listen(8050, () => {
  console.log("Website is listening at 8050");
});

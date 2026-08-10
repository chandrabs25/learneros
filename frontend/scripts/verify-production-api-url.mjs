import fs from "node:fs";
import path from "node:path";

const staticDir = path.resolve(".next/static");
const expectedApiUrl = process.env.NEXT_PUBLIC_API_URL
  || "https://learneros-backend.fly.dev";
const forbiddenApiUrl = "http://localhost:8000";

function javascriptFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return javascriptFiles(entryPath);
    return entry.isFile() && entry.name.endsWith(".js") ? [entryPath] : [];
  });
}

if (!fs.existsSync(staticDir)) {
  throw new Error(`Next.js static output was not found at ${staticDir}`);
}

const bundles = javascriptFiles(staticDir);
const bundleText = bundles.map((file) => fs.readFileSync(file, "utf8")).join("\n");

if (bundleText.includes(forbiddenApiUrl)) {
  throw new Error(
    `Production bundle contains forbidden API URL ${forbiddenApiUrl}. `
    + "Set NEXT_PUBLIC_API_URL at build time."
  );
}

if (!bundleText.includes(expectedApiUrl)) {
  throw new Error(
    `Production bundle does not contain the expected API URL ${expectedApiUrl}.`
  );
}

console.log(`Verified production API URL: ${expectedApiUrl}`);

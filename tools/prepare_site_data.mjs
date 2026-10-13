import { createReadStream, createWriteStream, existsSync, renameSync, rmSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";
import { createGzip } from "node:zlib";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const jsonPath = resolve(root, "data/dashboard-data.json");
const gzipPath = `${jsonPath}.gz`;

async function writeAtomically(target, input, transform) {
  const temporary = `${target}.tmp`;
  try {
    await pipeline(createReadStream(input), transform, createWriteStream(temporary));
    renameSync(temporary, target);
  } catch (error) {
    rmSync(temporary, { force: true });
    throw error;
  }
}

if (!existsSync(jsonPath)) throw new Error(`Missing cleaned dashboard data: ${jsonPath}`);
await writeAtomically(gzipPath, jsonPath, createGzip({ level: 9 }));
console.log(`Compressed GitHub dashboard data: ${statSync(gzipPath).size} bytes`);


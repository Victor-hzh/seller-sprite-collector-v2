import { createReadStream, createWriteStream, existsSync, renameSync, rmSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { pipeline } from "node:stream/promises";
import { fileURLToPath } from "node:url";
import { createGunzip, createGzip } from "node:zlib";

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

if (process.argv.includes("--compress")) {
  if (!existsSync(jsonPath)) throw new Error(`Missing dashboard data: ${jsonPath}`);
  await writeAtomically(gzipPath, jsonPath, createGzip({ level: 9 }));
  console.log(`Compressed dashboard data: ${statSync(gzipPath).size} bytes`);
} else if (!existsSync(jsonPath)) {
  if (!existsSync(gzipPath)) throw new Error(`Missing dashboard data: ${jsonPath} or ${gzipPath}`);
  await writeAtomically(jsonPath, gzipPath, createGunzip());
  console.log(`Restored dashboard data: ${statSync(jsonPath).size} bytes`);
}

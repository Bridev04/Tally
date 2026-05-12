import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const root = fileURLToPath(new URL("..", import.meta.url));

function listFiles(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) {
      return listFiles(path);
    }
    return path;
  });
}

const sourceFiles = listFiles(join(root, "app"))
  .concat(listFiles(join(root, "src")))
  .filter((path) => /\.(ts|tsx)$/.test(path));

const source = sourceFiles.map((path) => readFileSync(path, "utf8")).join("\n");

const checks = [
  ["uses Expo SecureStore", source.includes("expo-secure-store")],
  ["does not use AsyncStorage", !source.includes("AsyncStorage")],
  ["saves token with SecureStore", source.includes("SecureStore.setItemAsync")],
  ["clears token with SecureStore", source.includes("SecureStore.deleteItemAsync")],
  ["validates email form input", source.includes("emailPattern")],
  ["validates register password length", source.includes("password.length < 8")],
  ["protects app navigation", source.includes("<Redirect href=\"/(auth)/login\"")],
  ["redirects authenticated users", source.includes("<Redirect href=\"/(app)\"")],
];

const failed = checks.filter(([, passed]) => !passed);

if (failed.length > 0) {
  for (const [name] of failed) {
    console.error(`Auth safety check failed: ${name}`);
  }
  process.exit(1);
}

console.log("Mobile auth safety checks passed.");

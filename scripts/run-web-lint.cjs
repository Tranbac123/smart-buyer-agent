#!/usr/bin/env node

const { spawn } = require("node:child_process");

const child = spawn(
  "npm",
  ["--workspace", "apps/web-app", "run", "lint"],
  {
    stdio: "inherit",
    shell: false,
  }
);

child.on("exit", (code, signal) => {
  if (signal) {
    process.exit(1);
  } else {
    process.exit(code ?? 1);
  }
});

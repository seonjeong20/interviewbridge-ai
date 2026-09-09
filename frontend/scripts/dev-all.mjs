import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const projectDir = path.resolve(frontendDir, "..");

const services = [
  {
    name: "spring",
    command: process.platform === "win32" ? "gradlew.bat" : "./gradlew",
    args: ["bootRun"],
    cwd: path.join(projectDir, "backend"),
  },
  {
    name: "python",
    command: process.platform === "win32" ? "python" : "python3",
    args: ["-m", "uvicorn", "api:app", "--reload", "--port", "8000"],
    cwd: path.join(projectDir, "python"),
  },
  {
    name: "frontend",
    command: process.platform === "win32" ? "npm.cmd" : "npm",
    args: ["run", "dev:frontend"],
    cwd: frontendDir,
  },
];

const children = new Map();
let stopping = false;

function prefixOutput(stream, label, destination) {
  let pending = "";

  stream.on("data", (chunk) => {
    const lines = (pending + chunk.toString()).split(/\r?\n/);
    pending = lines.pop() ?? "";

    for (const line of lines) {
      destination.write(`[${label}] ${line}\n`);
    }
  });

  stream.on("end", () => {
    if (pending) destination.write(`[${label}] ${pending}\n`);
  });
}

function stopAll(exitCode = 0) {
  if (stopping) return;
  stopping = true;

  for (const child of children.values()) {
    if (child.exitCode !== null) continue;

    try {
      if (process.platform === "win32") child.kill("SIGTERM");
      else process.kill(-child.pid, "SIGTERM");
    } catch {
      // The process may already have exited.
    }
  }

  setTimeout(() => process.exit(exitCode), 500);
}

for (const service of services) {
  const child = spawn(service.command, service.args, {
    cwd: service.cwd,
    env: process.env,
    detached: process.platform !== "win32",
    stdio: ["inherit", "pipe", "pipe"],
  });

  children.set(service.name, child);
  prefixOutput(child.stdout, service.name, process.stdout);
  prefixOutput(child.stderr, service.name, process.stderr);

  child.on("error", (error) => {
    console.error(`[${service.name}] 실행 실패: ${error.message}`);
    stopAll(1);
  });

  child.on("exit", (code, signal) => {
    if (stopping) return;
    console.error(
      `[${service.name}] 서버가 종료되었습니다 (${signal ?? `exit ${code}`}).`,
    );
    stopAll(code ?? 1);
  });
}

process.on("SIGINT", () => stopAll(0));
process.on("SIGTERM", () => stopAll(0));

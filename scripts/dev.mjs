// Starts the FastAPI detector alongside the Next.js dev server; stopping the page stops the API.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";

const venvPython = process.platform === "win32" ? "venv/Scripts/python.exe" : "venv/bin/python";
const python = existsSync(venvPython) ? venvPython : "python";

const api = spawn(python, ["-m", "uvicorn", "api.main:app", "--app-dir", "src", "--port", "8000"], { stdio: "inherit" });
const web = spawn("next", ["dev"], { stdio: "inherit", shell: true });

web.on("exit", (code) => {
  api.kill();
  process.exit(code ?? 0);
});

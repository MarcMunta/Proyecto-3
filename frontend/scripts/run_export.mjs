// Lanza scripts/export_data.py con el Python del entorno virtual del repositorio.
// Orden de búsqueda: variable PYTHON, ../.venv (Windows o Unix) y, por último, "python".
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const raiz = resolve(aqui, "..", "..");
const candidatos = [
  process.env.PYTHON,
  join(raiz, ".venv", "Scripts", "python.exe"),
  join(raiz, ".venv", "bin", "python"),
].filter(Boolean);
const python = candidatos.find((c) => existsSync(c)) ?? "python";

const r = spawnSync(python, [join(aqui, "export_data.py"), ...process.argv.slice(2)], {
  stdio: "inherit",
  cwd: raiz,
});
if (r.error) {
  console.error(`No se pudo ejecutar Python (${python}): ${r.error.message}`);
  console.error("Define PYTHON con la ruta a .venv\\Scripts\\python.exe del repositorio.");
}
process.exit(r.status ?? 1);

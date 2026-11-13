// Genera la geometría estática del mapa a partir de los límites municipales oficiales
// (Eurostat GISCO, LAU 2024, EPSG:4326), ya descargados en data/raw/municipios por la fase de ingesta.
//
//   public/data/provincias.geojson          52 provincias (disolución de sus municipios), simplificadas
//   public/data/municipios/<código>.geojson municipios de cada provincia, con más detalle (se cargan al hacer zoom)
//
// Las provincias se obtienen disolviendo los municipios por los 2 primeros dígitos del código INE,
// así encajan exactamente con sus municipios (incluidas Baleares y Canarias, que en NUTS-3 van por islas).
//
// Uso:  npm run geo                       (busca ../data/raw/municipios/gisco_lau_2024_4326.shp.zip)
//       npm run geo -- --lau <ruta.shp.zip>
// Si no tienes los datos raw: scripts\descargar_datos_raw.ps1 en la raíz del repositorio, o descarga
// https://gisco-services.ec.europa.eu/distribution/v2/lau/shp/LAU_RG_01M_2024_4326.shp.zip
import mapshaper from "mapshaper";
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const front = resolve(aqui, "..");
const raiz = resolve(front, "..");
const arg = process.argv.indexOf("--lau");
const lau = arg > -1 ? resolve(process.argv[arg + 1]) : join(raiz, "data", "raw", "municipios", "gisco_lau_2024_4326.shp.zip");
if (!existsSync(lau)) {
  console.error(`No encuentro ${lau}.\nEjecuta scripts\\descargar_datos_raw.ps1 en la raíz del repo o pasa --lau <ruta>.`);
  process.exit(1);
}

const salida = join(front, "public", "data");
const dirMun = join(salida, "municipios");
const tmp = join(front, ".geo-tmp");
rmSync(tmp, { recursive: true, force: true });
rmSync(dirMun, { recursive: true, force: true });
mkdirSync(tmp, { recursive: true });
mkdirSync(dirMun, { recursive: true });

const q = (p) => `"${p.replaceAll("\\", "/")}"`;
const base = [
  `-i ${q(lau)} encoding=utf8`,
  `-filter "CNTR_CODE == 'ES'"`,
  `-each "ine = GISCO_ID.slice(3); prov = ine.slice(0, 2); nombre = LAU_NAME; area_km2 = Math.round(AREA_KM2 * 10) / 10"`,
  `-filter-fields ine,prov,nombre,area_km2`,
].join(" ");

console.log("Municipios por provincia…");
await mapshaper.runCommands(
  `${base} -simplify interval=90 keep-shapes -clean -split prov -o ${q(tmp + "/")} format=geojson precision=0.00001`,
);
for (const f of readdirSync(tmp)) {
  const m = f.match(/(\d{2})\.json$/);
  if (m) renameSync(join(tmp, f), join(dirMun, `${m[1]}.geojson`));
}

console.log("Provincias (disolución)…");
await mapshaper.runCommands(
  `${base} -dissolve prov -simplify interval=450 keep-shapes -clean -o ${q(join(tmp, "provincias.json"))} format=geojson precision=0.0001 ` +
  `-points inner -o ${q(join(tmp, "etiquetas.json"))} format=geojson precision=0.001`,
);
const etiquetas = Object.fromEntries(
  JSON.parse(readFileSync(join(tmp, "etiquetas.json"), "utf8")).features.map((f) => [f.properties.prov, f.geometry.coordinates]),
);

console.log("Contexto (Portugal, Francia, Andorra)…");
await mapshaper.runCommands(
  `-i ${q(lau)} encoding=utf8 -filter "['PT','FR','AD'].indexOf(CNTR_CODE) > -1" ` +
  `-clip bbox=-10.5,35.5,5.5,45.5 -dissolve CNTR_CODE -simplify interval=1500 keep-shapes -clean ` +
  `-o ${q(join(salida, "contexto.geojson"))} format=geojson precision=0.001`,
);

const meta = JSON.parse(readFileSync(join(front, "src", "data", "provincias.json"), "utf8"));
const porCodigo = Object.fromEntries(meta.map((p) => [p.codigo, p]));
const gj = JSON.parse(readFileSync(join(tmp, "provincias.json"), "utf8"));

const bbox = (geom) => {
  let b = [Infinity, Infinity, -Infinity, -Infinity];
  const walk = (c) => {
    if (typeof c[0] === "number") {
      b = [Math.min(b[0], c[0]), Math.min(b[1], c[1]), Math.max(b[2], c[0]), Math.max(b[3], c[1])];
    } else c.forEach(walk);
  };
  walk(geom.coordinates);
  return b.map((v) => Math.round(v * 1e4) / 1e4);
};

const contar = {};
for (const f of readdirSync(dirMun)) {
  const g = JSON.parse(readFileSync(join(dirMun, f), "utf8"));
  contar[f.slice(0, 2)] = { n: g.features.length, area: g.features.reduce((s, x) => s + (x.properties.area_km2 || 0), 0) };
}

gj.features = gj.features
  .filter((f) => porCodigo[f.properties.prov])
  .map((f, i) => ({
    type: "Feature",
    id: i + 1,
    properties: {
      codigo: f.properties.prov,
      nombre: porCodigo[f.properties.prov].nombre,
      n_municipios: contar[f.properties.prov]?.n ?? null,
      area_km2: contar[f.properties.prov] ? Math.round(contar[f.properties.prov].area) : null,
      bbox: bbox(f.geometry),
      etiqueta: etiquetas[f.properties.prov] ?? null,
    },
    geometry: f.geometry,
  }));
writeFileSync(join(salida, "provincias.geojson"), JSON.stringify(gj));
rmSync(tmp, { recursive: true, force: true });

const kb = (p) => Math.round(readFileSync(p).length / 1024);
console.log(`OK: ${gj.features.length} provincias (${kb(join(salida, "provincias.geojson"))} KB), ` +
  `${Object.keys(contar).length} ficheros de municipios, ${Object.values(contar).reduce((s, c) => s + c.n, 0)} municipios.`);

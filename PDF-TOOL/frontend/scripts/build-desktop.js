// Cross-platform helper: builds the static desktop site into ./out
const { spawnSync } = require("child_process");
const env = { ...process.env, PDFTOOL_DESKTOP: "1", NEXT_PUBLIC_API_BASE: "same-origin" };
const r = spawnSync("npx", ["next", "build"], { stdio: "inherit", env, shell: true });
process.exit(r.status ?? 1);

// Bootstrap the pinned pure Python wheels before stlite resolves its own
// dependencies. This avoids querying PyPI or choosing different versions later.
export async function loadPyodide(options) {
  const runtime = await import("./vendor/pyodide/pyodide.mjs");
  const python = await runtime.loadPyodide({
    ...options,
    indexURL: new URL("./vendor/pyodide/", import.meta.url).href,
  });
  await python.loadPackage("micropip");
  const response = await fetch(new URL("./bootstrap-wheels.json", import.meta.url));
  if (!response.ok) throw new Error(`Wheel manifest: HTTP ${response.status}`);
  const wheels = (await response.json()).map(url => new URL(url, import.meta.url).href);
  const micropip = python.pyimport("micropip");
  try {
    await micropip.install.callKwargs(wheels, { deps: false });
  } finally {
    micropip.destroy();
  }
  return python;
}

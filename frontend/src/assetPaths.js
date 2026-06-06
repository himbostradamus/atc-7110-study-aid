const configuredBase = import.meta.env.BASE_URL || "/";

export function assetUrl(path) {
  const cleanPath = String(path || "").replace(/^\/+/, "");
  const base = configuredBase.endsWith("/") ? configuredBase : `${configuredBase}/`;
  return `${base}${cleanPath}`;
}

export function isStaticDeploy() {
  return Boolean(
    window.__ATC_STATIC_DEPLOY__
    || import.meta.env.VITE_ATC_STATIC_DEPLOY === "1"
    || import.meta.env.VITE_ATC_STATIC_DEPLOY === "true",
  );
}

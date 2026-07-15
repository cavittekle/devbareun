const routeAliases = new Map([
  ["/", "/index.html"],
  ["/workspace", "/dashboard.html"],
  ["/super-admin", "/admin.html"],
  ["/super-admin/login", "/admin.html"],
]);

const securityHeaders = {
  "Content-Security-Policy": "default-src 'self'; img-src 'self' data: https:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://*.supabase.co https://*.railway.app https://*.up.railway.app https://api.lemonsqueezy.com; frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

function applyHeaders(response, pathname) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(securityHeaders)) headers.set(name, value);

  if (pathname.startsWith("/assets/")) {
    headers.set("Cache-Control", "public, max-age=31536000, immutable");
  } else if (pathname.endsWith(".html") || pathname === "/") {
    headers.set("Cache-Control", "public, max-age=0, must-revalidate");
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function fetchAsset(request, env, pathname) {
  const assetUrl = new URL(request.url);
  assetUrl.pathname = pathname;
  return env.ASSETS.fetch(new Request(assetUrl, request));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let pathname = routeAliases.get(url.pathname) ?? url.pathname;

    const projectMatch = pathname.match(/^\/projects\/([^/]+)$/);
    if (projectMatch) {
      pathname = "/project-detail.html";
      url.searchParams.set("id", decodeURIComponent(projectMatch[1]));
    } else if (!/\.[a-z0-9]+$/i.test(pathname) && pathname !== "/") {
      pathname = `${pathname}.html`;
    }

    let response = await fetchAsset(new Request(url, request), env, pathname);
    if (response.status === 404 && pathname !== "/404.html") {
      const notFound = await fetchAsset(request, env, "/404.html");
      response = new Response(notFound.body, {
        status: 404,
        headers: notFound.headers,
      });
    }

    return applyHeaders(response, pathname);
  },
};

import { getAdminIdentity } from "../_shared/access.js";

export async function onRequest({ request, env, next }) {
  const identity = await getAdminIdentity(request, env);
  if (!identity) {
    return new Response(
      `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Admin access required</title><body style="font:16px system-ui;background:#f6f3ec;color:#17261f;padding:8vh 8vw"><h1>Admin access required</h1><p>This review console is restricted through Cloudflare Access.</p></body></html>`,
      {
        status: 401,
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "no-store",
          "x-robots-tag": "noindex, nofollow",
        },
      },
    );
  }
  return next();
}

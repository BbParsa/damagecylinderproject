// Cloudflare Pages Function: GET /api/data
// Binds to D1 Database (env.DB)

export async function onRequestGet(context) {
  const { env } = context;

  if (!env.DB) {
    return new Response(JSON.stringify({ 
      error: "D1 Database binding 'DB' not found in environment." 
    }), {
      status: 500,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }

  try {
    const { results } = await env.DB.prepare(
      "SELECT * FROM damaged_cylinders ORDER BY id ASC"
    ).all();

    // Map SQLite 0/1 back to boolean for is_completed
    const records = (results || []).map(r => ({
      ...r,
      is_completed: Boolean(r.is_completed)
    }));

    return new Response(JSON.stringify({
      records: records,
      count: records.length,
      source: "Cloudflare D1 Database",
      server_time: new Date().toISOString()
    }), {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Cache-Control": "public, max-age=10, s-maxage=10"
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ 
      error: err.message 
    }), {
      status: 500,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
}

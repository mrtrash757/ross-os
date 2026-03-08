// Simple health check endpoint
export default async (req) => {
  return new Response(JSON.stringify({
    status: "ok",
    service: "ross-os",
    timestamp: new Date().toISOString(),
    env: {
      coda: !!process.env.CODA_API_TOKEN,
      supabase: !!process.env.SUPABASE_URL,
    }
  }, null, 2), {
    headers: { 'Content-Type': 'application/json' }
  });
};

export const config = {
  runtime: 'edge',
};

export default async function handler(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get('id');
  
  if (!id) {
    return new Response('Missing Google Drive file ID', { status: 400 });
  }

  // Google Drive direct download URL
  const url = `https://drive.google.com/uc?export=download&id=${id}`;
  
  try {
    const fetchHeaders = new Headers();
    const range = req.headers.get('range');
    if (range) {
      fetchHeaders.set('range', range);
    }

    const response = await fetch(url, { headers: fetchHeaders });
    
    // Create new headers based on the response
    const headers = new Headers(response.headers);
    // Add CORS headers so the frontend can read the JSON
    headers.set('Access-Control-Allow-Origin', '*');
    
    return new Response(response.body, {
      status: response.status,
      headers
    });
  } catch (error) {
    return new Response(`Error fetching from Google Drive`, { status: 500 });
  }
}

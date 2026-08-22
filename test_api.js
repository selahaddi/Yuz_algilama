const fetch = require('node-fetch');
const dotenv = require('dotenv');
dotenv.config();

async function run() {
  const res = await fetch(process.env.SUPABASE_URL + '/rest/v1/events?select=*', {
    headers: {
      'apikey': process.env.SUPABASE_ANON_KEY,
      'Authorization': 'Bearer ' + process.env.SUPABASE_ANON_KEY
    }
  });
  const data = await res.json();
  console.log(data);
}
run();

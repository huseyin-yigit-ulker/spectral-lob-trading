import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

let client;

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Supabase URL veya KEY bulunamadi! Local ortamda test yapiyorsaniz 'frontend/.env' dosyasina VITE_SUPABASE_URL ve VITE_SUPABASE_ANON_KEY ekleyin.");
  // Uygulamanin cokmemesi icin sahte bir obje dondur
  client = {
    from: () => ({
      select: () => ({
        order: () => ({ limit: () => Promise.resolve({ data: [] }) }),
        eq: () => ({ gte: () => Promise.resolve({ data: [] }) }),
      })
    })
  };
} else {
  client = createClient(supabaseUrl, supabaseAnonKey, {
    db: {
      schema: 'quant_v5'
    }
  });
}

export const supabase = client;

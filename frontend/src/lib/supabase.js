import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Supabase URL veya KEY bulunamadi. Lutfen .env dosyasini kontrol edin.")
}

export const supabase = createClient(supabaseUrl || "", supabaseAnonKey || "", {
  db: {
    schema: 'quant_v5'
  }
})

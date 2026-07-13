// Supabase connection for the public, read-only vending map.
// The ANON key is safe to expose in a client app: the vending_* tables have
// public SELECT RLS policies, and the accounting tables have NO policies (stay blocked).
// Fill in SUPABASE_ANON_KEY from: Supabase dashboard -> Project Settings -> API -> "anon public".
window.SUPABASE_URL = "https://ikhcbncnaojrndilmnnd.supabase.co";
window.SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGNibmNuYW9qcm5kaWxtbm5kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3MDc5NjYsImV4cCI6MjA5NzI4Mzk2Nn0.pOUaGdf2KA5a26UbR4V5TSkZAzoIEjA4UWKqZvsGOx4";

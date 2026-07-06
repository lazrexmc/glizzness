// Supabase connection for the public catering booking form.
// The ANON key is safe to expose: the catering_leads table allows INSERT only via the
// anon role (RLS) and has NO read policy, so the public can submit a lead but cannot read
// any leads back. Same key as the vending map.
window.SUPABASE_URL = "https://ikhcbncnaojrndilmnnd.supabase.co";
window.SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGNibmNuYW9qcm5kaWxtbm5kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3MDc5NjYsImV4cCI6MjA5NzI4Mzk2Nn0.pOUaGdf2KA5a26UbR4V5TSkZAzoIEjA4UWKqZvsGOx4";

// The booking form falls back to these if a submit fails. REPLACE the placeholders with the
// real Glizzness booking phone + email so customers always have a way through.
window.GLIZZNESS_PHONE = "573-000-0000";           // TODO: real booking phone (tel/text)
window.GLIZZNESS_EMAIL = "catering@glizzness.com"; // TODO: real booking email

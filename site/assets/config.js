/* The Glizzness — site config (safe to expose).
   The Supabase ANON key can only INSERT into catering_leads (RLS: no read policy),
   so the public can submit a booking but cannot read any leads back. Same project
   as the vending map + catering page. */
window.SUPABASE_URL = "https://ikhcbncnaojrndilmnnd.supabase.co";
window.SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGNibmNuYW9qcm5kaWxtbm5kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3MDc5NjYsImV4cCI6MjA5NzI4Mzk2Nn0.pOUaGdf2KA5a26UbR4V5TSkZAzoIEjA4UWKqZvsGOx4";

/* Booking + ordering contact */
window.GLIZZNESS_PHONE    = "314-266-8636";
window.GLIZZNESS_EMAIL    = "glizzness@gmail.com";
window.GLIZZNESS_DOORDASH = "https://www.doordash.com/store/38788821";

/* Social — TODO: confirm the exact handles/URLs before launch. Leave blank to hide. */
window.GLIZZNESS_FACEBOOK  = "";
window.GLIZZNESS_INSTAGRAM = "";

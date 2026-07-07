// Supabase connection for the public catering booking form.
// The ANON key is safe to expose: the catering_leads table allows INSERT only via the
// anon role (RLS) and has NO read policy, so the public can submit a lead but cannot read
// any leads back. Same key as the vending map.
window.SUPABASE_URL = "https://ikhcbncnaojrndilmnnd.supabase.co";
window.SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlraGNibmNuYW9qcm5kaWxtbm5kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3MDc5NjYsImV4cCI6MjA5NzI4Mzk2Nn0.pOUaGdf2KA5a26UbR4V5TSkZAzoIEjA4UWKqZvsGOx4";

// Booking contact — used for the "call/text/email us" fallback if a form submit ever fails.
window.GLIZZNESS_PHONE = "314-266-8636";
window.GLIZZNESS_EMAIL = "glizzness@gmail.com";

// DoorDash storefront URL. Paste your Glizzness DoorDash store link here to reveal the
// "Order on DoorDash" button (it stays hidden while this still says PASTE_YOUR_STORE).
// Find it: DoorDash merchant portal -> your store -> the public storefront URL, e.g.
//   https://www.doordash.com/store/glizzness-columbia-XXXXXXXX/
window.GLIZZNESS_DOORDASH = "https://www.doordash.com/store/38788821";

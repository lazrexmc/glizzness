/* The Glizzness — Scout Board shared auth + helpers (PRIVATE, gated pages only).
   Loaded by hub/, scout/, and hub/desk after supabase-js (unpkg) + config.js.

   Security: the anon key in config.js is public, but the three Scout tables have RLS with
   NO anon policy — logged out, this key can read/write nothing. After a Supabase Auth login,
   supabase-js sends the user's JWT (role = authenticated) on every call, which the
   `to authenticated` policies allow. The login gate is the real wall. */
(function () {
  "use strict";

  var _client = null;
  function client() {
    if (!_client) {
      if (!window.supabase || !window.SUPABASE_URL) {
        throw new Error("Scout: supabase-js or config.js failed to load.");
      }
      _client = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY, {
        auth: { persistSession: true, autoRefreshToken: true }
      });
    }
    return _client;
  }

  /* Current session (or null). */
  async function getSession() {
    var res = await client().auth.getSession();
    return res.data ? res.data.session : null;
  }

  /* Gate a page: returns the session, or bounces to the hub login (remembering where
     we were headed). Call at the top of scout/ and hub/desk. */
  async function requireSession() {
    var session = await getSession();
    if (!session) {
      var next = encodeURIComponent(location.pathname + location.search);
      location.replace("/hub/?next=" + next);
      return null;
    }
    return session;
  }

  async function signIn(email, password) {
    return client().auth.signInWithPassword({ email: email, password: password });
  }

  async function signOut() {
    try { await client().auth.signOut(); } catch (e) {}
    location.replace("/hub/");
  }

  function currentEmail(session) {
    return session && session.user ? (session.user.email || "") : "";
  }

  /* Short label ('lance'/'trint' from the email local-part, else the email) for thread authorship. */
  function authorTag(session) {
    var email = currentEmail(session).toLowerCase();
    if (email.indexOf("trint") === 0 || email.indexOf("james") === 0 || email.indexOf("jason") === 0) return "trint";
    if (email.indexOf("lance") === 0 || email.indexOf("laz") === 0) return "lance";
    return email || "user";
  }

  /* HTML-escape untrusted text before injecting into innerHTML. */
  function esc(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /* Wire a "Log out" control if the page has one (id="logout"). */
  function wireLogout() {
    var btn = document.getElementById("logout");
    if (btn) btn.addEventListener("click", function (e) { e.preventDefault(); signOut(); });
  }

  window.Scout = {
    client: client,
    getSession: getSession,
    requireSession: requireSession,
    signIn: signIn,
    signOut: signOut,
    currentEmail: currentEmail,
    authorTag: authorTag,
    esc: esc,
    wireLogout: wireLogout
  };
})();

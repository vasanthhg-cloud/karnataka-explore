/* Karnataka Explore - browser demo mode.
 *
 * This file powers sign-in, booking, the demo payment step, tickets, booking
 * history and a small admin console entirely in the browser, so the static
 * GitHub Pages build behaves like the Flask app. Data lives in localStorage.
 *
 * It is a DEMO: passwords are hashed with a toy function (not cryptography),
 * there is no server, and nothing leaves the device. The real implementation
 * is the Flask app in this repository.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* storage                                                             */
  /* ------------------------------------------------------------------ */
  var K = {
    users: "kx_demo_users",
    session: "kx_demo_session",
    bookings: "kx_demo_bookings",
    admin: "kx_demo_admin",
    seq: "kx_demo_seq"
  };

  var ADMIN = { email: "admin@karnatakaexplore.in", pass: "Admin@123" };

  function hash(text) {                    // toy hash, demo only
    var h = 5381;
    for (var i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
    return "h" + Math.abs(h).toString(36);
  }

  function read(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) { return fallback; }
  }
  function write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  }

  var Store = {
    users: function () { return read(K.users, []); },
    saveUsers: function (list) { write(K.users, list); },
    session: function () { return read(K.session, null); },
    setSession: function (v) { write(K.session, v); },
    bookings: function () { return read(K.bookings, []); },
    saveBookings: function (list) { write(K.bookings, list); },
    adminSession: function () { return read(K.admin, false); },
    setAdmin: function (v) { write(K.admin, v); },

    currentUser: function () {
      var s = Store.session();
      if (!s) return null;
      return Store.users().filter(function (u) { return u.id === s.userId; })[0] || null;
    },

    register: function (data) {
      var users = Store.users();
      var email = (data.email || "").trim().toLowerCase();
      if (!/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(email)) return { error: "Enter a valid email address." };
      if (!/^[6-9]\d{9}$/.test((data.mobile || "").trim())) return { error: "Enter a valid 10-digit mobile number." };
      if ((data.password || "").length < 8) return { error: "Password must be at least 8 characters." };
      if (data.password !== data.confirm) return { error: "The two passwords do not match." };
      if (users.some(function (u) { return u.email === email; })) return { error: "That email is already registered." };
      var user = {
        id: "u" + Date.now().toString(36),
        name: (data.name || "").trim(),
        email: email,
        mobile: (data.mobile || "").trim(),
        district: data.district || "",
        pass: hash(data.password),
        created: new Date().toISOString()
      };
      users.push(user);
      Store.saveUsers(users);
      Store.setSession({ userId: user.id });
      return { user: user };
    },

    login: function (identity, password) {
      var key = (identity || "").trim().toLowerCase();
      var user = Store.users().filter(function (u) {
        return u.email === key || u.mobile === key;
      })[0];
      if (!user || user.pass !== hash(password || "")) return { error: "Those details did not match an account." };
      Store.setSession({ userId: user.id });
      return { user: user };
    },

    logout: function () { Store.setSession(null); },

    adminLogin: function (email, password) {
      if ((email || "").trim().toLowerCase() !== ADMIN.email || password !== ADMIN.pass) {
        return { error: "Invalid administrator credentials." };
      }
      Store.setAdmin(true);
      return { ok: true };
    },

    nextRef: function () {
      var n = read(K.seq, 100000) + 1;
      write(K.seq, n);
      return "KX-" + n.toString(36).toUpperCase() + Math.random().toString(36).slice(2, 5).toUpperCase();
    },

    createBooking: function (b) {
      var list = Store.bookings();
      b.ref = Store.nextRef();
      b.status = "Pending";
      b.paymentStatus = "Unpaid";
      b.created = new Date().toISOString();
      list.push(b);
      Store.saveBookings(list);
      return b;
    },

    pay: function (ref, method, ok) {
      var list = Store.bookings();
      var b = list.filter(function (x) { return x.ref === ref; })[0];
      if (!b) return null;
      b.txn = "DEMO" + Math.floor(Math.random() * 1e10).toString().padStart(10, "0");
      b.method = method;
      if (ok) { b.paymentStatus = "Paid"; b.status = "Confirmed"; }
      else { b.paymentStatus = "Failed"; }
      Store.saveBookings(list);
      return b;
    },

    booking: function (ref) {
      return Store.bookings().filter(function (b) { return b.ref === ref; })[0] || null;
    },

    cancel: function (ref) {
      var list = Store.bookings();
      var b = list.filter(function (x) { return x.ref === ref; })[0];
      if (!b) return null;
      b.status = "Cancelled";
      Store.saveBookings(list);
      return b;
    },

    setStatus: function (ref, status) {
      var list = Store.bookings();
      var b = list.filter(function (x) { return x.ref === ref; })[0];
      if (b) { b.status = status; Store.saveBookings(list); }
      return b;
    },

    myBookings: function () {
      var user = Store.currentUser();
      if (!user) return [];
      return Store.bookings().filter(function (b) { return b.userId === user.id; })
        .sort(function (a, b) { return a.created < b.created ? 1 : -1; });
    }
  };

  /* ------------------------------------------------------------------ */
  /* pricing - mirrors the Flask rules                                   */
  /* ------------------------------------------------------------------ */
  var TAX = { destination: 0.05, homestay: 0.12, guide: 0.18 };

  function money(n) {
    return "₹" + Math.round(n || 0).toLocaleString("en-IN");
  }

  function quote(type, unitPrice, quantity) {
    var subtotal = Math.round(unitPrice * quantity * 100) / 100;
    var tax = Math.round(subtotal * (TAX[type] || 0.05) * 100) / 100;
    return { subtotal: subtotal, tax: tax, total: Math.round((subtotal + tax) * 100) / 100 };
  }

  /* ------------------------------------------------------------------ */
  /* data                                                                */
  /* ------------------------------------------------------------------ */
  var DATA = { destinations: [], homestays: [], guides: [] };
  var DATA_READY = false;

  function loadData() {
    if (DATA_READY) return Promise.resolve(DATA);
    return fetch("../data/items.json").then(function (r) { return r.json(); })
      .then(function (json) { DATA = json; DATA_READY = true; return DATA; })
      .catch(function () { return DATA; });
  }

  function findItem(type, slug) {
    var pool = type === "homestay" ? DATA.homestays : (type === "guide" ? DATA.guides : DATA.destinations);
    return (pool || []).filter(function (i) { return String(i.slug) === String(slug); })[0] || null;
  }

  function unitPrice(type, item) {
    if (!item) return 0;
    if (type === "homestay") return item.price;
    if (type === "guide") return item.fee;
    return item.price;
  }

  /* ------------------------------------------------------------------ */
  /* tiny view helpers                                                   */
  /* ------------------------------------------------------------------ */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function el(id) { return document.getElementById(id); }
  function go(hash) { location.hash = hash; }
  function today(offset) {
    var d = new Date();
    d.setDate(d.getDate() + (offset || 0));
    return d.toISOString().slice(0, 10);
  }

  function header(title, sub) {
    return '<div class="demo-head"><a href="../index.html" class="demo-back">← Back to the site</a>' +
      '<h1>' + esc(title) + "</h1>" + (sub ? '<p class="muted">' + sub + "</p>" : "") + "</div>";
  }

  function flash(msg, kind) {
    var box = el("demo-flash");
    if (!box) return;
    box.innerHTML = '<div class="flash ' + (kind || "success") + '" style="position:static;margin-bottom:1rem">' +
      esc(msg) + "</div>";
    setTimeout(function () { box.innerHTML = ""; }, 5000);
  }

  /* ------------------------------------------------------------------ */
  /* views                                                               */
  /* ------------------------------------------------------------------ */
  var Views = {};

  Views.login = function (params) {
    var u = Store.currentUser();
    if (u) { go("#/bookings"); return; }
    el("demo-root").innerHTML = header("Sign in", "Demo mode: accounts are stored in this browser only.") +
      '<div class="panel" style="max-width:440px">' +
      '<div class="field"><label>Email or mobile</label><input class="input" id="li-id" autocomplete="username"></div>' +
      '<div class="field"><label>Password</label><div class="pw-wrap">' +
      '<input class="input" id="li-pw" type="password" autocomplete="current-password">' +
      '<button type="button" class="pw-toggle" data-pw>Show</button></div></div>' +
      '<button class="btn btn-primary btn-block" id="li-go">Sign in</button>' +
      '<p class="muted center" style="margin-top:1rem">New here? <a href="#/register">Create an account</a></p>' +
      '<p class="hint center">Demo account: demo@karnatakaexplore.in / Demo@1234</p>' +
      "</div>";
    el("li-go").onclick = function () {
      var r = Store.login(el("li-id").value, el("li-pw").value);
      if (r.error) { flash(r.error, "error"); return; }
      go(params.next || "#/bookings");
    };
    el("li-pw").addEventListener("keydown", function (e) { if (e.key === "Enter") el("li-go").click(); });
  };

  Views.register = function () {
    var districts = ["Bagalkote", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru Urban", "Bidar",
      "Chamarajanagara", "Chikkaballapura", "Chikkamagaluru", "Chitradurga", "Dakshina Kannada",
      "Davanagere", "Dharwad", "Gadag", "Hassan", "Haveri", "Kalaburagi", "Kodagu", "Kolar", "Koppal",
      "Mandya", "Mysuru", "Raichur", "Ramanagara", "Shivamogga", "Tumakuru", "Udupi", "Uttara Kannada",
      "Vijayapura", "Vijayanagara", "Yadgir"];
    el("demo-root").innerHTML = header("Create an account", "Demo mode: stored in this browser only.") +
      '<div class="panel" style="max-width:560px"><div class="form-grid">' +
      '<div class="field full"><label>Full name</label><input class="input" id="rg-name"></div>' +
      '<div class="field"><label>Email</label><input class="input" id="rg-email" type="email"></div>' +
      '<div class="field"><label>Mobile</label><input class="input" id="rg-mobile" maxlength="10" inputmode="numeric"></div>' +
      '<div class="field"><label>Password</label><div class="pw-wrap">' +
      '<input class="input" id="rg-pw" type="password"><button type="button" class="pw-toggle" data-pw>Show</button></div>' +
      '<div class="hint">At least 8 characters.</div></div>' +
      '<div class="field"><label>Confirm password</label><input class="input" id="rg-pw2" type="password"></div>' +
      '<div class="field full"><label>District</label><select class="select" id="rg-district">' +
      districts.map(function (d) { return '<option>' + d + "</option>"; }).join("") +
      "</select></div></div>" +
      '<button class="btn btn-primary btn-block" id="rg-go">Create account</button>' +
      '<p class="muted center" style="margin-top:1rem">Already registered? <a href="#/login">Sign in</a></p>' +
      "</div>";
    el("rg-go").onclick = function () {
      var r = Store.register({
        name: el("rg-name").value, email: el("rg-email").value, mobile: el("rg-mobile").value,
        password: el("rg-pw").value, confirm: el("rg-pw2").value, district: el("rg-district").value
      });
      if (r.error) { flash(r.error, "error"); return; }
      go("#/bookings");
    };
  };

  Views.book = function (params) {
    var type = params.type || "destination";
    var item = findItem(type, params.slug);
    if (!item) { el("demo-root").innerHTML = header("Not found") + '<div class="notice">That listing does not exist.</div>'; return; }
    var user = Store.currentUser();
    if (!user) {
      go("#/login?next=" + encodeURIComponent("#/book?type=" + type + "&slug=" + params.slug));
      return;
    }
    var price = unitPrice(type, item);
    var fields = "";
    if (type === "homestay") {
      fields = '<div class="field"><label>Check-in</label><input class="input" type="date" id="bk-in" value="' + today(1) + '" min="' + today(0) + '"></div>' +
        '<div class="field"><label>Check-out</label><input class="input" type="date" id="bk-out" value="' + today(2) + '" min="' + today(1) + '"></div>' +
        '<div class="field"><label>Guests</label><input class="input" type="number" id="bk-visitors" value="2" min="1" max="' + (item.max_guests || 8) + '"></div>' +
        '<div class="field"><label>Rooms</label><input class="input" type="number" id="bk-rooms" value="1" min="1" max="' + (item.rooms || 2) + '"></div>';
    } else if (type === "guide") {
      fields = '<div class="field"><label>Start date</label><input class="input" type="date" id="bk-date" value="' + today(1) + '" min="' + today(0) + '"></div>' +
        '<div class="field"><label>Days</label><input class="input" type="number" id="bk-nights" value="1" min="1" max="14"></div>' +
        '<div class="field"><label>Visitors</label><input class="input" type="number" id="bk-visitors" value="2" min="1" max="20"></div>';
    } else {
      fields = '<div class="field"><label>Visit date</label><input class="input" type="date" id="bk-date" value="' + today(1) + '" min="' + today(0) + '"></div>' +
        '<div class="field"><label>Visitors</label><input class="input" type="number" id="bk-visitors" value="2" min="1" max="20"></div>';
    }
    el("demo-root").innerHTML = header("Book " + esc(item.name), esc(item.district) + " · " + money(price) +
      (type === "homestay" ? " per night" : (type === "guide" ? " per day" : " per person"))) +
      '<div class="split"><div class="panel"><div class="form-grid">' + fields + "</div>" +
      '<button class="btn btn-primary" id="bk-go">Continue to payment</button></div>' +
      '<div class="panel"><h3>Booking summary</h3>' +
      '<div class="summary-row"><span>' + (type === "homestay" ? "Price per night" : (type === "guide" ? "Fee per day" : "Entry fee")) +
      "</span><span>" + money(price) + "</span></div>" +
      '<div class="summary-row"><span>Taxes and fees</span><span>added at payment</span></div>' +
      '<div class="notice info" style="margin-top:1rem">Demo payment — no money is charged.</div></div></div>';

    el("bk-go").onclick = function () {
      var visitors = parseInt(el("bk-visitors").value, 10) || 1;
      var qty = visitors, nights = 0, rooms = 1, checkin = null, checkout = null, date = null;
      if (type === "homestay") {
        checkin = el("bk-in").value; checkout = el("bk-out").value;
        rooms = parseInt(el("bk-rooms").value, 10) || 1;
        nights = Math.round((new Date(checkout) - new Date(checkin)) / 86400000);
        if (!(nights > 0)) { flash("Check-out must be after check-in.", "error"); return; }
        qty = nights * rooms;
      } else if (type === "guide") {
        date = el("bk-date").value;
        nights = parseInt(el("bk-nights").value, 10) || 1;
        qty = nights;
      } else {
        date = el("bk-date").value;
      }
      var q = quote(type, price, qty);
      var b = Store.createBooking({
        userId: user.id, userName: user.name, type: type, itemSlug: item.slug, itemName: item.name,
        district: item.district, image: item.image || "", date: date, checkin: checkin, checkout: checkout,
        nights: nights, rooms: rooms, visitors: visitors, unitPrice: price,
        subtotal: q.subtotal, tax: q.tax, total: q.total
      });
      go("#/pay?ref=" + b.ref);
    };
  };

  Views.pay = function (params) {
    var b = Store.booking(params.ref);
    if (!b) { el("demo-root").innerHTML = header("Not found") + '<div class="notice">No booking with that reference.</div>'; return; }
    if (b.paymentStatus === "Paid") { go("#/ticket?ref=" + b.ref); return; }
    el("demo-root").innerHTML = header("Demo payment", "Booking " + esc(b.ref)) +
      '<div class="split"><div>' +
      '<div class="notice" style="margin-bottom:1rem"><span>⚠</span><div><b>DEMO PAYMENT — NO REAL MONEY WILL BE DEDUCTED</b><br>' +
      "No card number, UPI PIN, OTP or bank password is collected anywhere in this project.</div></div>" +
      '<div class="panel"><h3>Payment method</h3><div class="pay-methods" style="margin-bottom:1rem">' +
      '<label class="pay-method"><input type="radio" name="pm" value="UPI" checked> UPI</label>' +
      '<label class="pay-method"><input type="radio" name="pm" value="Debit Card"> Debit card</label>' +
      '<label class="pay-method"><input type="radio" name="pm" value="Credit Card"> Credit card</label>' +
      '<label class="pay-method"><input type="radio" name="pm" value="Net Banking"> Net banking</label></div>' +
      '<div class="actions"><button class="btn btn-primary" id="pay-ok">Simulate successful payment</button>' +
      '<button class="btn btn-danger" id="pay-fail">Simulate failed payment</button></div></div></div>' +
      '<div class="panel"><h3>Booking summary</h3>' +
      '<div class="summary-row"><span>Booking ID</span><b>' + esc(b.ref) + "</b></div>" +
      '<div class="summary-row"><span>Item</span><span>' + esc(b.itemName) + "</span></div>" +
      (b.type === "homestay"
        ? '<div class="summary-row"><span>Stay</span><span>' + esc(b.checkin) + " → " + esc(b.checkout) + "</span></div>"
        : '<div class="summary-row"><span>Date</span><span>' + esc(b.date) + "</span></div>") +
      '<div class="summary-row"><span>Visitors</span><span>' + b.visitors + "</span></div>" +
      '<hr class="divider">' +
      '<div class="summary-row"><span>Subtotal</span><span>' + money(b.subtotal) + "</span></div>" +
      '<div class="summary-row"><span>Taxes and fees</span><span>' + money(b.tax) + "</span></div>" +
      '<div class="summary-row total"><span>Total</span><span>' + money(b.total) + "</span></div></div></div>";

    function method() {
      var picked = document.querySelector('input[name="pm"]:checked');
      return picked ? picked.value : "UPI";
    }
    el("pay-ok").onclick = function () { Store.pay(b.ref, method(), true); go("#/ticket?ref=" + b.ref); };
    el("pay-fail").onclick = function () {
      Store.pay(b.ref, method(), false);
      flash("The demo payment failed. You can try again — nothing was charged.", "error");
      go("#/pay?ref=" + b.ref);
    };
  };

  Views.ticket = function (params) {
    var b = Store.booking(params.ref);
    if (!b) { el("demo-root").innerHTML = header("Not found") + '<div class="notice">No booking with that reference.</div>'; return; }
    var verifyUrl = location.href.split("#")[0] + "?ref=" + b.ref;
    var qrMarkup = "";
    try {
      if (typeof qrcode === "function") {
        var q = qrcode(0, "M");
        q.addData(verifyUrl);
        q.make();
        qrMarkup = q.createSvgTag({ cellSize: 4, margin: 2 });
      }
    } catch (e) { qrMarkup = ""; }
    if (!qrMarkup) {
      qrMarkup = '<div style="width:110px;height:110px;display:grid;place-items:center;border:1px dashed var(--line-strong);border-radius:10px;font-size:.7rem;text-align:center;padding:6px">' +
        esc(b.ref) + "</div>";
    }
    el("demo-root").innerHTML = header("Your ticket", "Booking " + esc(b.ref)) +
      '<div class="ticket" id="ticket-card">' +
      '<div class="ticket-head"><div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap">' +
      '<div><span class="badge" style="background:rgba(255,255,255,.18);color:#fff">' + esc(b.status) + "</span>" +
      '<h2 style="color:#fff;margin:.5rem 0 .2rem">' + esc(b.itemName) + "</h2>" +
      '<p style="color:rgba(255,255,255,.82);margin:0">' + esc(b.district) + "</p></div>" +
      '<div style="text-align:right"><small style="color:rgba(255,255,255,.7)">BOOKING ID</small>' +
      '<div style="font-size:1.15rem;font-weight:800">' + esc(b.ref) + "</div></div></div></div>" +
      '<div class="ticket-body"><div class="ticket-grid">' +
      "<div><span>Traveller</span><b>" + esc(b.userName) + "</b></div>" +
      "<div><span>Booked on</span><b>" + esc(b.created.slice(0, 10)) + "</b></div>" +
      (b.type === "homestay"
        ? "<div><span>Check-in</span><b>" + esc(b.checkin) + "</b></div><div><span>Check-out</span><b>" + esc(b.checkout) + "</b></div>" +
          "<div><span>Nights / rooms</span><b>" + b.nights + " / " + b.rooms + "</b></div>"
        : "<div><span>Date</span><b>" + esc(b.date) + "</b></div>") +
      "<div><span>Visitors</span><b>" + b.visitors + "</b></div>" +
      "<div><span>Total</span><b>" + money(b.total) + "</b></div>" +
      "<div><span>Payment</span><b>" + esc(b.paymentStatus) + " (demo)</b></div>" +
      "<div><span>Transaction</span><b>" + esc(b.txn || "-") + "</b></div></div>" +
      '<div class="qr-box" style="margin-top:22px"><div style="width:110px;height:110px;flex:none">' + qrMarkup + '</div>' +
      "<div><b>Scan to verify this booking</b><p class='hint' style='margin:0'>Reference " + esc(b.ref) + "</p></div></div>" +
      '<div class="actions" style="margin-top:22px" id="ticket-actions">' +
      '<button class="btn btn-primary" onclick="window.print()">Download / print ticket (PDF)</button>' +
      '<a class="btn btn-ghost" href="#/bookings">My bookings</a></div>' +
      '<p class="hint" style="margin-top:1rem">Demo project — the payment shown here was simulated.</p>' +
      "</div></div>";
  };

  Views.bookings = function () {
    var user = Store.currentUser();
    if (!user) { go("#/login?next=" + encodeURIComponent("#/bookings")); return; }
    var list = Store.myBookings();
    var rows = list.map(function (b) {
      return "<tr><td><b>" + esc(b.ref) + "</b></td><td>" + esc(b.itemName) + "</td>" +
        "<td>" + esc(b.date || b.checkin || "-") + "</td><td>" + b.visitors + "</td>" +
        "<td>" + money(b.total) + "</td>" +
        '<td><span class="badge ' + (b.paymentStatus === "Paid" ? "ok" : (b.paymentStatus === "Failed" ? "danger" : "warn")) + '">' +
        esc(b.paymentStatus) + "</span></td>" +
        '<td><span class="badge ' + (b.status === "Confirmed" ? "ok" : (b.status === "Cancelled" ? "danger" : "warn")) + '">' +
        esc(b.status) + "</span></td>" +
        '<td><div class="actions"><a class="btn btn-soft btn-sm" href="#/ticket?ref=' + b.ref + '">View ticket</a>' +
        (b.paymentStatus !== "Paid" ? '<a class="btn btn-primary btn-sm" href="#/pay?ref=' + b.ref + '">Pay</a>' : "") +
        (b.status !== "Cancelled" ? '<button class="btn btn-danger btn-sm" data-cancel="' + b.ref + '">Cancel</button>' : "") +
        "</div></td></tr>";
    }).join("");

    el("demo-root").innerHTML = header("My bookings", "Signed in as " + esc(user.name)) +
      '<div class="actions" style="margin-bottom:1rem">' +
      '<a class="btn btn-ghost btn-sm" href="#/profile">Profile</a>' +
      '<button class="btn btn-ghost btn-sm" id="logout">Sign out</button></div>' +
      (list.length
        ? '<div class="table-wrap"><table><thead><tr><th>Booking</th><th>Item</th><th>Date</th><th>Visitors</th>' +
          "<th>Total</th><th>Payment</th><th>Status</th><th></th></tr></thead><tbody>" + rows + "</tbody></table></div>"
        : '<div class="empty"><h3>No bookings yet.</h3><a class="btn btn-primary" href="../destinations/index.html">Browse destinations</a></div>');

    var out = el("logout");
    if (out) out.onclick = function () { Store.logout(); go("#/login"); };
    document.querySelectorAll("[data-cancel]").forEach(function (btn) {
      btn.onclick = function () {
        if (!confirm("Cancel this booking?")) return;
        Store.cancel(btn.getAttribute("data-cancel"));
        Views.bookings();
      };
    });
  };

  Views.profile = function () {
    var user = Store.currentUser();
    if (!user) { go("#/login?next=" + encodeURIComponent("#/profile")); return; }
    el("demo-root").innerHTML = header("My profile") +
      '<div class="panel" style="max-width:520px"><div class="form-grid">' +
      '<div class="field full"><label>Name</label><input class="input" value="' + esc(user.name) + '" disabled></div>' +
      '<div class="field"><label>Email</label><input class="input" value="' + esc(user.email) + '" disabled></div>' +
      '<div class="field"><label>Mobile</label><input class="input" value="' + esc(user.mobile) + '" disabled></div>' +
      '<div class="field full"><label>District</label><input class="input" value="' + esc(user.district) + '" disabled></div></div>' +
      '<p class="hint">Demo mode keeps profiles read-only. The Flask app supports editing.</p>' +
      '<a class="btn btn-ghost" href="#/bookings">Back to bookings</a></div>';
  };

  Views.admin = function () {
    if (!Store.adminSession()) {
      el("demo-root").innerHTML = header("Administrator sign in", "Separate from visitor accounts.") +
        '<div class="panel" style="max-width:420px">' +
        '<div class="field"><label>Email</label><input class="input" id="ad-email"></div>' +
        '<div class="field"><label>Password</label><div class="pw-wrap">' +
        '<input class="input" id="ad-pw" type="password"><button type="button" class="pw-toggle" data-pw>Show</button></div></div>' +
        '<button class="btn btn-primary btn-block" id="ad-go">Sign in</button>' +
        '<p class="hint center" style="margin-top:1rem">admin@karnatakaexplore.in / Admin@123</p></div>';
      el("ad-go").onclick = function () {
        var r = Store.adminLogin(el("ad-email").value, el("ad-pw").value);
        if (r.error) { flash(r.error, "error"); return; }
        Views.admin();
      };
      return;
    }
    var bookings = Store.bookings().slice().reverse();
    var users = Store.users();
    var paid = bookings.filter(function (b) { return b.paymentStatus === "Paid"; });
    var revenue = paid.reduce(function (s, b) { return s + b.total; }, 0);
    var rows = bookings.map(function (b) {
      return "<tr><td><b>" + esc(b.ref) + "</b></td><td>" + esc(b.userName) + "</td><td>" + esc(b.itemName) + "</td>" +
        "<td>" + money(b.total) + "</td><td>" + esc(b.paymentStatus) + "</td>" +
        '<td><select class="select" data-status="' + b.ref + '" style="padding:.3rem;font-size:.82rem">' +
        ["Pending", "Confirmed", "Cancelled", "Completed"].map(function (s) {
          return '<option ' + (b.status === s ? "selected" : "") + ">" + s + "</option>";
        }).join("") + "</select></td></tr>";
    }).join("");

    el("demo-root").innerHTML = header("Admin console", "Demo mode — data lives in this browser.") +
      '<div class="actions" style="margin-bottom:1rem"><button class="btn btn-ghost btn-sm" id="ad-out">Sign out</button></div>' +
      '<div class="grid cols-4" style="margin-bottom:1.5rem">' +
      '<div class="stat-card"><span>Registered users</span><b>' + users.length + "</b></div>" +
      '<div class="stat-card"><span>Bookings</span><b>' + bookings.length + "</b></div>" +
      '<div class="stat-card"><span>Paid</span><b>' + paid.length + "</b></div>" +
      '<div class="stat-card"><span>Demo revenue</span><b>' + money(revenue) + "</b></div></div>" +
      (bookings.length
        ? '<div class="table-wrap"><table><thead><tr><th>Booking</th><th>Traveller</th><th>Item</th><th>Total</th>' +
          "<th>Payment</th><th>Status</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
        : '<div class="empty"><h3>No bookings yet.</h3></div>');

    el("ad-out").onclick = function () { Store.setAdmin(false); go("#/login"); };
    document.querySelectorAll("[data-status]").forEach(function (sel) {
      sel.onchange = function () {
        Store.setStatus(sel.getAttribute("data-status"), sel.value);
        flash("Booking status updated.");
      };
    });
  };

  /* ------------------------------------------------------------------ */
  /* router                                                              */
  /* ------------------------------------------------------------------ */
  function parse() {
    var raw = (location.hash || "#/login").replace(/^#\/?/, "");
    var parts = raw.split("?");
    var params = {};
    (parts[1] || "").split("&").forEach(function (pair) {
      if (!pair) return;
      var kv = pair.split("=");
      params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
    return { view: parts[0] || "login", params: params };
  }

  function render() {
    var route = parse();
    var fn = Views[route.view] || Views.login;
    el("demo-root").innerHTML = '<p class="muted center">Loading…</p>';
    loadData().then(function () { fn(route.params); });
    window.scrollTo(0, 0);
  }

  document.addEventListener("click", function (e) {
    var pw = e.target.closest("[data-pw]");
    if (pw) {
      var input = pw.parentElement.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
      pw.textContent = input.type === "password" ? "Show" : "Hide";
    }
  });

  window.addEventListener("hashchange", render);
  document.addEventListener("DOMContentLoaded", function () {
    if (!location.hash) location.hash = "#/login";
    render();
  });

  // exposed for the Node test harness
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { Store: Store, quote: quote, hash: hash, money: money };
  }
})();

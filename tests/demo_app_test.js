/* Unit tests for the browser demo store (no DOM needed). */
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; }
};
global.document = { addEventListener() {}, querySelectorAll: () => [], getElementById: () => null };
global.window = { addEventListener() {} };
global.fetch = () => Promise.reject(new Error("no network in test"));

const app = require("../scripts/static_app/app.js");
const { Store, quote } = app;

let fails = 0;
function check(label, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + label + (cond ? "" : "  " + (extra || "")));
  if (!cond) fails++;
}

// registration + validation
check("rejects bad email", !!Store.register({ name: "A", email: "nope", mobile: "9876543210", password: "Testing1", confirm: "Testing1" }).error);
check("rejects short password", !!Store.register({ name: "A", email: "a@b.com", mobile: "9876543210", password: "abc", confirm: "abc" }).error);
check("rejects mismatched passwords", !!Store.register({ name: "A", email: "a@b.com", mobile: "9876543210", password: "Testing1", confirm: "Testing2" }).error);
const reg = Store.register({ name: "Test User", email: "Test@Example.com", mobile: "9876543210", password: "Testing123", confirm: "Testing123", district: "Mysuru" });
check("registers a user", !!reg.user, JSON.stringify(reg));
check("lowercases email", reg.user && reg.user.email === "test@example.com");
check("duplicate email rejected", !!Store.register({ name: "B", email: "test@example.com", mobile: "9876543211", password: "Testing123", confirm: "Testing123" }).error);

// login
Store.logout();
check("wrong password rejected", !!Store.login("test@example.com", "wrong").error);
check("login by email", !!Store.login("test@example.com", "Testing123").user);
check("currentUser set", Store.currentUser() && Store.currentUser().name === "Test User");
Store.logout();
check("login by mobile", !!Store.login("9876543210", "Testing123").user);

// pricing mirrors the Flask rules
const qd = quote("destination", 100, 3);
check("destination tax 5%", qd.subtotal === 300 && qd.tax === 15 && qd.total === 315, JSON.stringify(qd));
const qh = quote("homestay", 3200, 2);
check("homestay tax 12%", qh.subtotal === 6400 && qh.tax === 768 && qh.total === 7168, JSON.stringify(qh));
const qg = quote("guide", 1800, 2);
check("guide tax 18%", qg.subtotal === 3600 && qg.tax === 648 && qg.total === 4248, JSON.stringify(qg));

// booking lifecycle
const b = Store.createBooking({ userId: Store.currentUser().id, userName: "Test User", type: "destination",
  itemSlug: "jog-falls", itemName: "Jog Falls", district: "Shivamogga", visitors: 2,
  subtotal: 40, tax: 2, total: 42 });
check("booking ref format", /^KX-[A-Z0-9]+$/.test(b.ref), b.ref);
check("booking starts unpaid", b.paymentStatus === "Unpaid" && b.status === "Pending");
check("appears in my bookings", Store.myBookings().length === 1);

const failed = Store.pay(b.ref, "UPI", false);
check("failed payment recorded", failed.paymentStatus === "Failed" && failed.status === "Pending");
check("txn generated", /^DEMO\d{10}$/.test(failed.txn), failed.txn);

const paid = Store.pay(b.ref, "UPI", true);
check("successful payment confirms", paid.paymentStatus === "Paid" && paid.status === "Confirmed");

check("admin rejects bad creds", !!Store.adminLogin("admin@karnatakaexplore.in", "wrong").error);
check("admin accepts good creds", Store.adminLogin("admin@karnatakaexplore.in", "Admin@123").ok === true);
check("admin session set", Store.adminSession() === true);

check("admin status change", Store.setStatus(b.ref, "Completed").status === "Completed");
check("cancel sets cancelled", Store.cancel(b.ref).status === "Cancelled");
check("booking lookup by ref", Store.booking(b.ref).ref === b.ref);
check("unknown ref returns null", Store.booking("KX-NOPE") === null);

// data isolation between users
Store.logout();
Store.register({ name: "Second", email: "second@example.com", mobile: "9876543212", password: "Testing123", confirm: "Testing123" });
check("second user sees no bookings", Store.myBookings().length === 0);

console.log(fails ? "\n" + fails + " FAILURES" : "\nALL DEMO-APP TESTS PASSED");
process.exit(fails ? 1 : 0);

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Hotspot Portal</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; background: #1a1a2e; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .card { background: white; border-radius: 12px; padding: 32px; width: 100%; max-width: 440px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
    h2 { text-align: center; margin-bottom: 6px; color: #1a1a2e; }
    p.sub { text-align: center; color: #888; margin-bottom: 24px; font-size: 14px; }
    .step { display: none; }
    .step.active { display: block; }
    input, select { padding: 10px 14px; border: 1px solid #ccc; border-radius: 8px; width: 100%; margin-bottom: 14px; font-size: 15px; }
    button { padding: 12px; background: #1a1a2e; color: white; border: none; border-radius: 8px; width: 100%; font-size: 15px; cursor: pointer; margin-bottom: 10px; }
    button.secondary { background: #eee; color: #333; }
    .package-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
    .package-item { border: 2px solid #eee; border-radius: 8px; padding: 14px; cursor: pointer; transition: 0.2s; }
    .package-item:hover { border-color: #1a1a2e; }
    .package-item.selected { border-color: #1a1a2e; background: #f0f0f8; }
    .package-item h4 { margin-bottom: 4px; }
    .package-item span { color: #888; font-size: 13px; }
    .success-icon { text-align: center; font-size: 60px; margin-bottom: 16px; }
    .info-box { background: #f4f4f4; border-radius: 8px; padding: 14px; margin-bottom: 16px; font-size: 14px; line-height: 1.8; }
    .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
    .tab-btn { flex: 1; padding: 10px; border: 2px solid #1a1a2e; border-radius: 8px; background: white; color: #1a1a2e; font-weight: bold; cursor: pointer; }
    .tab-btn.active { background: #1a1a2e; color: white; }
  </style>
</head>
<body>
<div class="card">

  <div id="step-welcome" class="step active">
    <h2>Hotspot Portal</h2>
    <p class="sub">Get online in seconds</p>
    <div class="tabs">
      <button class="tab-btn active" onclick="selectType('new')">New User</button>
      <button class="tab-btn" onclick="selectType('returning')">Returning User</button>
    </div>

    <div id="new-user-form">
      <input id="reg-name" placeholder="Full Name" />
      <input id="reg-phone" placeholder="Phone Number (+2547XXXXXXXX)" />
      <input id="reg-router" placeholder="Router / Location (e.g. Room 4, Cyber)" />
      <button onclick="registerUser()">Continue</button>
    </div>

    <div id="returning-user-form" style="display:none;">
      <input id="ret-phone" placeholder="Phone Number (+2547XXXXXXXX)" />
      <button onclick="findUser()">Find My Account</button>
    </div>
  </div>

  <div id="step-packages" class="step">
    <h2>Choose a Package</h2>
    <p class="sub">Select a plan that works for you</p>
    <div class="package-list" id="package-list"></div>
    <button onclick="proceedToPayment()">Pay Now</button>
    <button class="secondary" onclick="goTo('step-welcome')">Back</button>
  </div>

  <div id="step-payment" class="step">
    <h2>Confirm Payment</h2>
    <p class="sub">M-Pesa STK Push will be sent to your phone</p>
    <div class="info-box" id="payment-summary"></div>
    <button onclick="sendSTK()">Send M-Pesa Prompt</button>
    <button class="secondary" onclick="goTo('step-packages')">Back</button>
  </div>

  <div id="step-waiting" class="step">
    <h2>Waiting for Payment</h2>
    <p class="sub">Check your phone and enter your M-Pesa PIN</p>
    <div style="text-align:center; margin: 30px 0;">
      <div id="countdown" style="font-size:40px; font-weight:bold; color:#1a1a2e;">60</div>
      <p style="color:#888; margin-top:8px;">seconds remaining</p>
    </div>
    <button class="secondary" onclick="goTo('step-packages')">Cancel</button>
  </div>

  <div id="step-success" class="step">
    <div class="success-icon">✓</div>
    <h2>You're Online!</h2>
    <p class="sub">Payment confirmed</p>
    <div class="info-box" id="success-summary"></div>
    <button onclick="window.location.href='http://google.com'">Start Browsing</button>
  </div>

  <div id="step-error" class="step">
    <div style="text-align:center; font-size:60px; margin-bottom:16px;">✗</div>
    <h2>Payment Failed</h2>
    <p class="sub" id="error-msg">Something went wrong. Please try again.</p>
    <button onclick="goTo('step-packages')">Try Again</button>
  </div>

</div>

<script>
  const API = "http://127.0.0.1:8000";
  let currentTenant = null;
  let selectedPackage = null;
  let countdownTimer = null;

  function goTo(stepId) {
    document.querySelectorAll(".step").forEach(s => s.classList.remove("active"));
    document.getElementById(stepId).classList.add("active");
  }

  function selectType(type) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    event.target.classList.add("active");
    document.getElementById("new-user-form").style.display = type === "new" ? "block" : "none";
    document.getElementById("returning-user-form").style.display = type === "returning" ? "block" : "none";
  }

  async function registerUser() {
    const name = document.getElementById("reg-name").value.trim();
    const phone = document.getElementById("reg-phone").value.trim();
    const router = document.getElementById("reg-router").value.trim();

    if (!name || !phone || !router) {
      alert("Please fill in all fields.");
      return;
    }

    const res = await fetch(`${API}/tenants/?name=${encodeURIComponent(name)}&phone=${encodeURIComponent(phone)}&router_name=${encodeURIComponent(router)}`, { method: "POST" });
    currentTenant = await res.json();
    loadPackages();
  }

  async function findUser() {
    const phone = document.getElementById("ret-phone").value.trim();
    const res = await fetch(`${API}/tenants/`);
    const tenants = await res.json();
    currentTenant = tenants.find(t => t.phone === phone);

    if (!currentTenant) {
      alert("Phone number not found. Please register as a new user.");
      return;
    }
    loadPackages();
  }

  async function loadPackages() {
    const res = await fetch(`${API}/packages/`);
    const packages = await res.json();
    const list = document.getElementById("package-list");
    list.innerHTML = "";
    packages.forEach(p => {
      const div = document.createElement("div");
      div.className = "package-item";
      div.innerHTML = `<h4>${p.name}</h4><span>${p.duration_days} days &mdash; KES ${p.price}</span>`;
      div.onclick = () => {
        document.querySelectorAll(".package-item").forEach(i => i.classList.remove("selected"));
        div.classList.add("selected");
        selectedPackage = p;
      };
      list.appendChild(div);
    });
    goTo("step-packages");
  }

  function proceedToPayment() {
    if (!selectedPackage) {
      alert("Please select a package.");
      return;
    }
    document.getElementById("payment-summary").innerHTML = `
      <b>Name:</b> ${currentTenant.name}<br>
      <b>Phone:</b> ${currentTenant.phone}<br>
      <b>Package:</b> ${selectedPackage.name}<br>
      <b>Duration:</b> ${selectedPackage.duration_days} days<br>
      <b>Amount:</b> KES ${selectedPackage.price}
    `;
    goTo("step-payment");
  }

  async function sendSTK() {
    goTo("step-waiting");
    startCountdown();

    const res = await fetch(`${API}/payments/stk-push`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: currentTenant.id,
        package_id: selectedPackage.id,
        phone: currentTenant.phone,
        amount: selectedPackage.price
      })
    });

    const data = await res.json();

    if (data.checkout_request_id) {
      pollPaymentStatus(data.checkout_request_id, data.subscription_id);
    } else {
      clearInterval(countdownTimer);
      document.getElementById("error-msg").textContent = data.detail || "STK Push failed.";
      goTo("step-error");
    }
  }

  function startCountdown() {
    let seconds = 60;
    document.getElementById("countdown").textContent = seconds;
    countdownTimer = setInterval(() => {
      seconds--;
      document.getElementById("countdown").textContent = seconds;
      if (seconds <= 0) {
        clearInterval(countdownTimer);
        goTo("step-error");
        document.getElementById("error-msg").textContent = "Payment timed out. Please try again.";
      }
    }, 1000);
  }

  async function pollPaymentStatus(checkoutRequestId, subscriptionId) {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      const res = await fetch(`${API}/payments/status/${checkoutRequestId}`);
      const data = await res.json();

      if (data.status === "confirmed") {
        clearInterval(interval);
        clearInterval(countdownTimer);
        document.getElementById("success-summary").innerHTML = `
          <b>Package:</b> ${selectedPackage.name}<br>
          <b>Duration:</b> ${selectedPackage.duration_days} days<br>
          <b>Amount Paid:</b> KES ${selectedPackage.price}<br>
          <b>M-Pesa Code:</b> ${data.mpesa_code}
        `;
        goTo("step-success");
      }

      if (data.status === "failed" || attempts >= 12) {
        clearInterval(interval);
        clearInterval(countdownTimer);
        document.getElementById("error-msg").textContent = "Payment not confirmed. Try again.";
        goTo("step-error");
      }
    }, 5000);
  }
</script>
</body>
</html>
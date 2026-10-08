# 📶 M-Pesa WiFi Hotspot Billing System

A full-stack open source WiFi hotspot billing system with M-Pesa STK Push payments and MikroTik router integration. Built for cybercafés, small businesses, and public WiFi hotspots across Kenya.

> Built with FastAPI · SQLite · MikroTik API · Safaricom Daraja

---

## 🧱 How It Works

```
Tenant connects to WiFi
        ↓
MikroTik redirects to payment portal
        ↓
Tenant enters phone number + selects plan
        ↓
M-Pesa STK Push sent to phone
        ↓
Tenant enters M-Pesa PIN
        ↓
System confirms payment
        ↓
MikroTik grants internet access automatically
        ↓
Access expires when subscription ends → blocked automatically
```

---

## 📁 Project Structure

```
hotspot-billing/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── database.py          # SQLite database setup
│   ├── models.py            # Database models
│   ├── crud.py              # Database operations
│   ├── notifications.py     # SMS/notification logic
│   ├── mikrotik.py          # MikroTik API integration
│   ├── routes/
│   │   └── tenants.py       # Tenant API routes
│   ├── .env.example         # Environment variables template
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Docker configuration
├── frontend/
│   ├── admin/
│   │   └── index.html       # Admin dashboard
│   └── portal/
│       └── index.html       # Tenant payment portal
└── docker-compose.yml       # Docker Compose setup
```

---

## ⚙️ Requirements

- Python 3.12+
- pip
- virtualenv
- MikroTik router (with Hotspot feature)
- Safaricom Daraja API account (`developer.safaricom.co.ke`)
- A public URL for M-Pesa callback (Railway, VPS, or ngrok for testing)

---

## 🚀 Local Setup

### Step 1 — Clone the project

```bash
git clone https://github.com/YOUR_USERNAME/hotspot-billing.git
cd hotspot-billing
```

### Step 2 — Create virtual environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Set up environment variables

```bash
cp .env.example .env
nano .env
```

Fill in your values:

```env
# M-Pesa Daraja
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=your_till_number
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=https://yourdomain.co.ke/mpesa/callback
MPESA_ENV=sandbox

# MikroTik
MIKROTIK_HOST=192.168.88.1
MIKROTIK_USER=admin
MIKROTIK_PASSWORD=your_mikrotik_password

# App
SECRET_KEY=your_secret_key_here
```

> ⚠️ Never commit your `.env` file to GitHub. It is already in `.gitignore`.

### Step 5 — Start the server

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process
```

### Step 6 — Open the app

| Page | URL |
|------|-----|
| API docs | `http://localhost:8000/docs` |
| Admin dashboard | `frontend/admin/index.html` |
| Tenant portal | `frontend/portal/index.html` |

---

## 🌐 Deployment (Railway.app)

### Step 1 — Push to GitHub

```bash
cd hotspot-billing
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/hotspot-billing.git
git push -u origin main
```

### Step 2 — Deploy on Railway

1. Go to `railway.app`
2. Click **New Project**
3. Select **Deploy from GitHub**
4. Select your `hotspot-billing` repo
5. Set root directory to `backend`
6. Add your environment variables
7. Click **Deploy**

### Step 3 — Update callback URL

Railway gives you a public URL like:
```
https://hotspot-billing-production.up.railway.app
```

Update `MPESA_CALLBACK_URL` in Railway:
```
https://hotspot-billing-production.up.railway.app/mpesa/callback
```

---

## 🔌 MikroTik Configuration

### Step 1 — Enable Hotspot

1. Open **WinBox** → connect to your MikroTik
2. Go to **IP → Hotspot**
3. Click **Hotspot Setup**
4. Follow the wizard on your WiFi interface

### Step 2 — Point login page to your system

In MikroTik Hotspot settings set:
```
Login Page URL: https://your-deployment-url/portal
```

### Step 3 — Enable API access

1. Go to **IP → Services** → Enable **API** on port `8728`
2. Go to **System → Users** → Add new user
3. Set policy to `api`

Update `.env`:
```env
MIKROTIK_HOST=192.168.88.1
MIKROTIK_USER=api_user
MIKROTIK_PASSWORD=api_password
```

---

## 💳 M-Pesa Daraja Setup

### Sandbox (Testing)

1. Go to `developer.safaricom.co.ke`
2. Sign up / Log in
3. Create new app → select **M-PESA Express Sandbox**
4. Copy **Consumer Key** and **Consumer Secret**
5. Add to your `.env`
6. Test using Safaricom sandbox test numbers

### Going Live (Production)

Requirements from your client:
- ✅ Till number or Paybill (Short Code)
- ✅ Business name (as registered with Safaricom)
- ✅ M-PESA business portal username (`business.safaricom.co.ke`)

Steps:
1. Log into Daraja portal
2. Click **Go Live** in the sidebar
3. Fill in organization details
4. Client receives OTP on their registered number
5. Enter OTP → submit
6. Wait **1–3 business days** for Safaricom approval

After approval, update `.env`:
```env
MPESA_ENV=production
MPESA_SHORTCODE=your_live_till_number
MPESA_CONSUMER_KEY=your_live_consumer_key
MPESA_CONSUMER_SECRET=your_live_consumer_secret
```

---

## 👤 Admin Dashboard Features

| Feature | Description |
|---------|-------------|
| View tenants | See all registered tenants and their status |
| Add tenant | Register a new tenant with name, phone, router |
| Enable/Disable | Toggle tenant internet access |
| Delete tenant | Remove a tenant permanently |
| Payment history | View all transactions |

---

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tenants/` | List all tenants |
| POST | `/tenants/` | Add new tenant |
| PUT | `/tenants/{id}/toggle` | Enable/Disable tenant |
| DELETE | `/tenants/{id}` | Delete tenant |
| POST | `/mpesa/callback` | M-Pesa payment callback |

Full interactive docs: `http://localhost:8000/docs`

---

## 🔄 Subscription Expiry Logic

- Tenant pays → system records exact payment timestamp
- Subscription countdown starts automatically
- When time expires → MikroTik blocks that MAC address
- Tenant must pay again to reconnect
- No manual action needed from admin

---

## 🛡️ Security Features

- JWT authentication on admin dashboard
- HTTPS enforced in production
- Rate limiting on all API routes
- Input validation to prevent SQL injection
- All secrets stored in environment variables
- CORS restricted to your domain only

---

## 🧰 Troubleshooting

### Server won't start

```bash
# Make sure you are in the backend folder
cd hotspot-billing/backend

# Activate virtual environment
source venv/bin/activate

# If hotspot.db is a folder instead of a file, remove it
rm -rf hotspot.db

# Start server
uvicorn main:app --reload
```

### M-Pesa callback not receiving

- Confirm `MPESA_CALLBACK_URL` is a **public HTTPS URL**
- Check deployment is running on Railway
- Check Daraja portal logs for errors
- For local testing use `cloudflared tunnel --url http://localhost:8000`

### MikroTik not granting access after payment

- Confirm API service is enabled on port `8728`
- Check `MIKROTIK_HOST` IP is correct
- Verify API user has correct policy permissions
- Check backend logs for connection errors

### Tenant cannot connect after payment

- Check MikroTik API connection in backend logs
- Verify MAC address whitelisting is working
- Confirm `mikrotik.py` is running without errors

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## ⭐ Support

If this project helped you, give it a star on GitHub!

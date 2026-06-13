# ⚙️ SmartPlanner AI — API Backend Codebase

This repository contains the multi-threaded Flask production microservice layer that powers the SmartPlanner AI application. It manages secure user identity operations through JWT tokens, exposes endpoints for dynamic talent pool allocations, and implements automated backend guardrails against developer resource burnout and misallocations.

🐍 **API Backend Codebase:** [https://github.com](https://github.com)

---

## 🛠️ Tech Stack & Requirements

* **Language Engine:** Python 3.10+
* **Framework Layer:** Flask / Gunicorn WSGI Web Server
* **Database Vault:** MongoDB Atlas (NoSQL Document Store Engine)
* **Identity Protocol:** PyJWT (JSON Web Token Signatures)

---

## 💻 Local Workspace Configuration

### Prerequisites
Ensure you have the following frameworks installed natively on your local machine:
* [Python 3.10 or higher](https://python.org)
* [MongoDB Atlas Account](https://mongodb.com) (or a running local MongoDB Instance)

### 1. Project Bootstrapping
Clone the backend repository, navigate to the system workspace, and create an isolated environment context:
```bash
git clone https://github.com.git
cd smart-resource-planner-backend

# Initialize virtual environment environment
python -m venv venv

# Activate workspace parameters (macOS/Linux)
source venv/bin/activate

# Activate workspace parameters (Windows CMD)
venv\Scripts\activate
```

### 2. Dependency Management
Install the necessary package manifests to populate the web server logic:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configurations
Create a production environment file named exactly `.env` in the root backend directory to contain system secrets securely:
```text
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/smart_planner?retryWrites=true&w=majority
JWT_SECRET=your_super_secret_jwt_signature_key_here
PORT=5000
FLASK_ENV=development
```

### 4. Running the Development Server
Execute the runtime command to spin up the system API layer locally:
```bash
python app.py
```
The active backend server will immediately begin listening for HTTPS requests at: `http://localhost:5000`

---

## 📋 Operational Endpoints Summary

| Route | Method | Access Requirement | Execution Target |
| :--- | :--- | :--- | :--- |
| `/api/auth/signup` | `POST` | Public Access | Creates a secure management record. |
| `/api/auth/login` | `POST` | Public Access | Emits valid client authorization keys. |
| `/api/employees` | `GET` / `POST` | `Bearer Token` Required | Fetches active talent pools or saves new engineers. |
| `/api/employees/<id>`| `PUT` | `Bearer Token` Required | Targets updates to discrete developer entries. |
| `/api/projects` | `GET` / `POST` | `Bearer Token` Required | Pulls operational system contracts or pipelines. |
| `/api/allocations` | `POST` | `Bearer Token` Required | Pins hours to a project using internal guardrails. |

---

## 🧪 Operational Check & Verification
You can rapidly test your local endpoint mapping by utilizing a terminal `curl` network request to check the base employee endpoint context:
```bash
curl -X GET http://localhost:5000/api/employees \
  -H "Authorization: Bearer <YOUR_GENERATED_JWT_TOKEN>"
```

# AI Business Twin

**AI Business Twin** is a comprehensive, AI-powered web application designed to help small and micro-business owners seamlessly analyze their business data. By simply uploading their messy CSV or Excel files, users get automated data cleaning, an interactive KPI dashboard, and an intelligent AI assistant capable of answering specific questions about their business performance.

---

## 🌟 Key Features

### 1. Secure Authentication & User Isolation
- Secure JWT-based registration and login system.
- Full multi-tenant data isolation: Each user manages their own unique business profile, and data is completely walled off from other users.

### 2. Intelligent Data Upload & Validation
- Drag-and-drop support for CSV and Excel files.
- **Auto-Mapping:** Intelligently detects columns (Sales, Inventory, Expenses) even if they are named poorly (e.g., "qty", "Revenue $", "sale date").
- **Automated Data Cleaning:** Validates data types, flags missing values, removes duplicates, and standardizes date formats before committing to the database.

### 3. Dynamic Analytics Dashboard
- **KPI Tracking:** Automatically calculates Total Revenue, Gross Profit, Profit Margins, Total Orders, Average Order Value, Total Expenses, and Stock levels.
- **Visual Insights:** Interactive CSS-based bar charts displaying monthly and daily revenue trends.
- **Top Performers:** Ranks top products by revenue and breaks down expenses by category.
- **Smart Alerts:** Automatically generates alerts for low stock, out-of-stock items, or high expense ratios.

### 4. AI Business Assistant
- Powered by **Google Gemini 2.0 Flash** (`google.genai`).
- Context-aware chatbot that receives a background prompt populated with the user's live KPI data, product stats, and inventory levels.
- Provides practical, data-grounded business advice, trend explanations, and actionable next steps.

### 5. What-If Scenario Engine
- An interactive testing sandbox to simulate business decisions.
- Users can test the impact of changing product prices, adjusting sales volumes, reducing expenses, or offering promotional discounts.
- Provides a side-by-side "Current vs. Projected" comparison showing the estimated impact on Revenue and Profit.

---

## 🛠 Technical Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) – High-performance asynchronous web framework for Python.
- **Database:** SQLite (for local development) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) ORM.
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/en/latest/) for database schema migrations.
- **Data Processing:** [Pandas](https://pandas.pydata.org/) & [OpenPyXL](https://openpyxl.readthedocs.io/en/stable/) for robust CSV/Excel parsing, validation, and cleaning.
- **AI Integration:** [Google GenAI SDK](https://github.com/googleapis/python-genai) (`google.genai`) to interface with the Gemini API.
- **Security:** `passlib` (bcrypt) for password hashing and `python-jose` for JWT generation/verification.

### Frontend
- **Templating:** [Jinja2](https://jinja.palletsprojects.com/) for server-side HTML rendering.
- **Styling:** Custom Vanilla CSS utilizing CSS variables, responsive Grid/Flexbox layouts, glassmorphism, and micro-animations for a premium feel. No heavy CSS frameworks were used, ensuring maximum performance and customizability.
- **Interactivity:** Vanilla JavaScript (ES6+) for DOM manipulation, asynchronous API fetching, and dynamic chart rendering.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A Google Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd business_twin
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add the following:
   ```env
   SECRET_KEY=your_super_secret_jwt_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   DATABASE_URL=sqlite:///./ai_business_twin.db
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

4. **Run the Application:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Access the App:**
   Open your browser and navigate to `http://127.0.0.1:8000`.

---

## 🧪 Testing

The application includes a comprehensive, in-process test suite (`test_all.py`) that covers all 12 phases of the application (Authentication, Data Validation, Analytics Engine, AI Assistant, Security Isolation, etc.).

To run the tests:
```bash
python test_all.py
```

---

## ⚠️ Current Limitations & Drawbacks (Future Improvements)

While the application is fully functional, there are a few architectural choices optimized for the current MVP that could be improved for a large-scale production release:

1. **Database Scalability (SQLite):** Currently uses SQLite for ease of setup. For a production environment with concurrent users, migrating to PostgreSQL (via updating the `DATABASE_URL` and SQLAlchemy bindings) is highly recommended to handle concurrent writes properly.
2. **In-Memory Data Processing:** The Pandas data validation pipeline loads entire uploaded files into memory. If users upload massive CSV files (e.g., millions of rows), this could cause memory spikes. A streaming chunk-based approach (e.g., `pd.read_csv(chunksize=...)`) would be better for enterprise-scale data.
3. **JWT Storage:** The frontend currently stores the JWT access token in `localStorage`. While standard for SPAs, storing JWTs in `HttpOnly` secure cookies provides better protection against Cross-Site Scripting (XSS) attacks.
4. **Single AI API Key:** The system currently utilizes a single server-side `GEMINI_API_KEY` for all users. In a multi-tenant SaaS environment, implementing a system for users to provide their own API keys or implementing strict usage quotas per user would prevent API rate limiting and excessive billing.
5. **Chart Libraries:** The dashboard charts are elegantly built using custom HTML/CSS bars for a lightweight footprint. For more complex visualizations (like interactive line graphs with tooltips and zooming), integrating a library like Chart.js or Recharts would be beneficial.

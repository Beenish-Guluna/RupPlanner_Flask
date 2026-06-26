# RupPlanner — Flask/Python Version

A personal finance tracker (income, expenses, budgets, goals) converted from RupPlanner - Laravel/Breeze to Python/Flask.

## Stack
- **Backend:** Python 3.10+ · Flask 3
- **Database:** MySQL (same schema as the Laravel project)
- **Frontend:** Jinja2 templates · Tailwind CSS (pre-built) · Alpine.js (via the included app.js)

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- MySQL server running locally
- `rupplanner_db` database created


### 2. Install Python dependencies

```bash
cd RupPlanner_Flask
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

Edit `.env` and set your MySQL credentials:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=my_db
DB_USERNAME=root
DB_PASSWORD=my_password
SECRET_KEY=some-random-secret
```

### 4. Run database migrations

```bash
flask init-db
```

This runs `migrations/schema.sql` which creates all tables:
`users`, `income_sources`, `incomes`, `expense_categories`, `expenses`, `budgets`, `goals`

### 5. Start the development server

```bash
flask run
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Project Structure

```
RupPlanner_Flask/
├── app.py                          # Flask application (routes + logic)
├── requirements.txt
├── .env                            # Environment variables
├── migrations/
│   └── schema.sql                  # MySQL DDL (same tables as Laravel)
├── static/
│   ├── css/app.css                 # Compiled Tailwind CSS (from original build)
│   └── js/app.js                   # Alpine.js bundle (from original build)
└── templates/
    ├── welcome.html                # Landing page
    ├── dashboard.html              # Dashboard (auth)
    ├── layouts/
    │   ├── app.html                # Authenticated layout (nav + slot)
    │   └── guest.html              # Guest layout (login/register)
    ├── auth/
    │   ├── login.html
    │   ├── register.html
    │   ├── forgot_password.html
    │   └── confirm_password.html
    ├── income_sources/
    │   ├── index.html
    │   ├── create.html
    │   └── edit.html
    └── profile/
        └── edit.html               # Profile + password + delete account
```

## Laravel → Flask mapping

| Laravel concept            | Flask equivalent                          |
|----------------------------|-------------------------------------------|
| `Route::resource()`        | Individual `@app.route` functions         |
| `Auth::id()`               | `session['user_id']`                      |
| `Auth::user()`             | `g.user` (loaded in `before_request`)     |
| `@csrf` token              | Not needed (Flask sessions are signed)    |
| `@method('PUT'/'DELETE')`  | Hidden `<input name="_method">`           |
| Blade `{{ $var }}`         | Jinja2 `{{ var }}`                        |
| `number_format($x, 2)`     | `{{ x \| number_format }}`                |
| `Hash::make()`             | `werkzeug.security.generate_password_hash`|
| `Hash::check()`            | `werkzeug.security.check_password_hash`   |
| `middleware('auth')`       | `@login_required` decorator               |
| `middleware('guest')`      | `@guest_required` decorator               |
| Laravel migrations         | `migrations/schema.sql` (run once)        |

## Notes

- Password reset emails are not implemented.
  The forgot-password page shows a generic success notice instead.
- The `.env` DB credentials mirror the original Laravel `.env` exactly.
- All Tailwind classes and Alpine.js interactivity are preserved via the same
  compiled assets from the original laravel project.

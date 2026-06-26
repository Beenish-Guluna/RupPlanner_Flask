from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'rupplanner-secret-key-change-in-production')

# MySQL Configuration
app.config['MYSQL_HOST'] = os.environ.get('DB_HOST', '127.0.0.1')
app.config['MYSQL_PORT'] = int(os.environ.get('DB_PORT', 3306))
app.config['MYSQL_USER'] = os.environ.get('DB_USERNAME', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('DB_DATABASE', 'rupplanner_db')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_login'))
        return f(*args, **kwargs)
    return decorated


def guest_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id is not None:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        g.user = cur.fetchone()
        cur.close()


# Welcome / Landing


@app.route('/')
def welcome():
    return render_template('welcome.html')



# Dashboard


@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM income_sources")
    total_income = float(cur.fetchone()['total'])

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = %s",
        (session['user_id'],)
    )
    total_expenses = float(cur.fetchone()['total'])

    remaining_balance = total_income - total_expenses

    cur.execute(
        "SELECT COUNT(*) as cnt FROM goals WHERE user_id = %s AND status = 'In Progress'",
        (session['user_id'],)
    )
    active_goals = cur.fetchone()['cnt']

    cur.close()
    return render_template(
        'dashboard.html',
        total_income=total_income,
        total_expenses=total_expenses,
        remaining_balance=remaining_balance,
        active_goals=active_goals,
    )



# Auth routes


@app.route('/register', methods=['GET', 'POST'])
@guest_required
def auth_register():
    errors = {}
    old = {}
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirmation = request.form.get('password_confirmation', '')
        old = {'name': name, 'email': email}

        if not name:
            errors['name'] = 'Name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters.'
        elif password != password_confirmation:
            errors['password'] = 'Passwords do not match.'

        if not errors:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                errors['email'] = 'Email already registered.'
            else:
                cur.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, generate_password_hash(password))
                )
                mysql.connection.commit()
                user_id = cur.lastrowid
                cur.close()
                session['user_id'] = user_id
                return redirect(url_for('dashboard'))
            cur.close()

    return render_template('auth/register.html', errors=errors, old=old)


@app.route('/login', methods=['GET', 'POST'])
@guest_required
def auth_login():
    errors = {}
    old = {}
    status = session.pop('status', None)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        old = {'email': email}

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user or not check_password_hash(user['password'], password):
            errors['email'] = 'These credentials do not match our records.'
        else:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))

    return render_template('auth/login.html', errors=errors, old=old, status=status)


@app.route('/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return redirect(url_for('welcome'))


@app.route('/forgot-password', methods=['GET', 'POST'])
@guest_required
def auth_forgot_password():
    status = None
    errors = {}
    if request.method == 'POST':
        # Password reset emails require mail setup; show a notice instead.
        status = 'If an account with that email exists, a reset link has been sent.'
    return render_template('auth/forgot_password.html', errors=errors, status=status)


@app.route('/confirm-password', methods=['GET', 'POST'])
@login_required
def auth_confirm_password():
    errors = {}
    if request.method == 'POST':
        password = request.form.get('password', '')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        cur.close()
        if not check_password_hash(user['password'], password):
            errors['password'] = 'The provided password is incorrect.'
        else:
            session['password_confirmed_at'] = True
            return redirect(url_for('dashboard'))
    return render_template('auth/confirm_password.html', errors=errors)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@app.route('/profile', methods=['GET'])
@login_required
def profile_edit():
    return render_template('profile/edit.html', user=g.user)


@app.route('/profile', methods=['POST'])
@login_required
def profile_update():
    method = request.form.get('_method', 'POST').upper()
    if method == 'PATCH':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        errors = {}

        if not name:
            errors['name'] = 'Name is required.'
        if not email:
            errors['email'] = 'Email is required.'

        if not errors:
            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE users SET name=%s, email=%s WHERE id=%s",
                (name, email, session['user_id'])
            )
            mysql.connection.commit()
            cur.close()
            session['status'] = 'profile-updated'
            return redirect(url_for('profile_edit'))

        return render_template('profile/edit.html', user=g.user, errors=errors)

    elif method == 'DELETE':
        password = request.form.get('password', '')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        if not check_password_hash(user['password'], password):
            flash('Incorrect password.', 'error')
            cur.close()
            return redirect(url_for('profile_edit'))
        cur.execute("DELETE FROM users WHERE id = %s", (session['user_id'],))
        mysql.connection.commit()
        cur.close()
        session.clear()
        return redirect(url_for('welcome'))

    return redirect(url_for('profile_edit'))


@app.route('/password', methods=['POST'])
@login_required
def password_update():
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('password', '')
    password_confirmation = request.form.get('password_confirmation', '')
    errors = {}

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cur.fetchone()

    if not check_password_hash(user['password'], current_password):
        errors['current_password'] = 'The current password is incorrect.'
    elif len(new_password) < 8:
        errors['password'] = 'New password must be at least 8 characters.'
    elif new_password != password_confirmation:
        errors['password'] = 'Passwords do not match.'

    if errors:
        cur.close()
        return render_template('profile/edit.html', user=g.user, password_errors=errors)

    cur.execute(
        "UPDATE users SET password=%s WHERE id=%s",
        (generate_password_hash(new_password), session['user_id'])
    )
    mysql.connection.commit()
    cur.close()
    session['status'] = 'password-updated'
    return redirect(url_for('profile_edit'))

# Income Sources (resource: index, create, store, edit, update, destroy)


@app.route('/income-sources')
@login_required
def income_sources_index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM income_sources ORDER BY source_id")
    sources = cur.fetchall()
    cur.close()
    return render_template('income_sources/index.html', sources=sources)


@app.route('/income-sources/create')
@login_required
def income_sources_create():
    return render_template('income_sources/create.html', errors={}, old={})


@app.route('/income-sources', methods=['POST'])
@login_required
def income_sources_store():
    source_name = request.form.get('source_name', '').strip()
    amount = request.form.get('amount', '').strip()
    errors = {}
    old = {'source_name': source_name, 'amount': amount}

    if not source_name:
        errors['source_name'] = 'Source name is required.'
    if not amount:
        errors['amount'] = 'Amount is required.'
    else:
        try:
            amount = float(amount)
            if amount < 0:
                errors['amount'] = 'Amount must be non-negative.'
        except ValueError:
            errors['amount'] = 'Amount must be a number.'

    if errors:
        return render_template('income_sources/create.html', errors=errors, old=old)

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO income_sources (source_name, amount) VALUES (%s, %s)",
        (source_name, amount)
    )
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('income_sources_index'))


@app.route('/income-sources/<int:id>/edit')
@login_required
def income_sources_edit(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM income_sources WHERE source_id = %s", (id,))
    source = cur.fetchone()
    cur.close()
    if not source:
        return "Not found", 404
    return render_template('income_sources/edit.html', source=source, errors={})


@app.route('/income-sources/<int:id>', methods=['POST'])
@login_required
def income_sources_update_or_delete(id):
    method = request.form.get('_method', 'POST').upper()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM income_sources WHERE source_id = %s", (id,))
    source = cur.fetchone()
    if not source:
        cur.close()
        return "Not found", 404

    if method == 'DELETE':
        cur.execute("DELETE FROM income_sources WHERE source_id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('income_sources_index'))

    # PUT / update
    source_name = request.form.get('source_name', '').strip()
    amount = request.form.get('amount', '').strip()
    errors = {}

    if not source_name:
        errors['source_name'] = 'Source name is required.'
    if not amount:
        errors['amount'] = 'Amount is required.'
    else:
        try:
            amount = float(amount)
            if amount < 0:
                errors['amount'] = 'Amount must be non-negative.'
        except ValueError:
            errors['amount'] = 'Amount must be a number.'

    if errors:
        cur.close()
        return render_template('income_sources/edit.html', source=source, errors=errors)

    cur.execute(
        "UPDATE income_sources SET source_name=%s, amount=%s WHERE source_id=%s",
        (source_name, amount, id)
    )
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('income_sources_index'))



# Template helpers / filters


@app.template_filter('number_format')
def number_format(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return value


@app.context_processor
def inject_globals():
    return {
        'session_status': session.pop('status', None),
        'current_user': g.user,
    }

# DB Initialization helper (run once)


@app.cli.command('init-db')
def init_db():
    """Create all tables in the MySQL database."""
    import click
    sql = open('migrations/schema.sql').read()
    cur = mysql.connection.cursor()
    for statement in sql.split(';'):
        stmt = statement.strip()
        if stmt:
            cur.execute(stmt)
    mysql.connection.commit()
    cur.close()
    click.echo('Database initialised.')


if __name__ == '__main__':
    app.run(debug=True)

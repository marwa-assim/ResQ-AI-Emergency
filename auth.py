from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from database import db
from db_models import User

auth_bp = Blueprint('auth', __name__)

def redirect_by_role(role):
    if role == 'ambulance':
        return redirect(url_for('ambulance_view'))
    elif role == 'volunteer':
        return redirect(url_for('volunteer_view'))
    elif role == 'patient':
        return redirect(url_for('patient_view'))
    return redirect(url_for('ambulance_view')) # fallback to main app view

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect_by_role(user.role)

    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        role = request.form.get('role', 'patient') # default to patient
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if user: 
            flash('Email address already exists')
            return redirect(url_for('auth.signup'))

        # Create new user, using the selected role
        new_user = User(email=email, name=name, role=role.lower())
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user) # Auto login
        return redirect_by_role(new_user.role)

    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

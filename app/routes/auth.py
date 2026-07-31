"""Authentication routes."""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms.auth import LoginForm, SignupForm
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    
    # DEBUG: Print request and form data before validation
    print("REQUEST METHOD:", request.method)
    print("FORM VALIDATE:", form.validate_on_submit())
    print("FORM ERRORS:", form.errors)
    print("EMAIL:", form.email.data)
    print("PASSWORD LENGTH:", len(form.password.data or ""))
    print("REQUEST FORM:", request.form)
    print("CSRF TOKEN:", request.form.get("csrf_token"))
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        
        # DEBUG: Print user query results
        print("USER FOUND:", user)
        if user:
            print("DB EMAIL:", user.email)
            print("PASSWORD CHECK:", user.check_password(form.password.data))
            print("IS ACTIVE:", user.is_active)

        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=form), 401

        if not user.is_active:
            flash("This account has been deactivated. Contact your administrator.", "warning")
            return render_template("auth/login.html", form=form), 403

        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        login_user(user, remember=form.remember_me.data)
        flash(f"Welcome back, {user.full_name}!", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/signup.html", form=form), 400

        user = User(
            email=email,
            full_name=form.full_name.data.strip()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))



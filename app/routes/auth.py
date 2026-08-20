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

    if request.method == "POST":
        print("=" * 50)
        print("LOGIN ATTEMPT")
        print("FORM ERRORS:", form.errors)
        print("EMAIL:", repr(form.email.data))
        print("PASSWORD LENGTH:", len(form.password.data or ""))
        print("CSRF PRESENT:", bool(request.form.get("csrf_token")))
        print("=" * 50)

    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()
        password = form.password.data or ""

        try:
            user = User.query.filter_by(email=email).first()

            if user is None or not user.check_password(password):
                flash("Invalid email or password.", "danger")
                return render_template("auth/login.html", form=form), 401

            if not user.is_active:
                flash(
                    "This account has been deactivated. Contact your administrator.",
                    "warning",
                )
                return render_template("auth/login.html", form=form), 403

            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            login_user(user, remember=form.remember_me.data)

            flash(f"Welcome back, {user.full_name}!", "success")

            next_page = request.args.get("next")

            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect(url_for("main.dashboard"))

        except Exception as exc:
            db.session.rollback()
            flash("A database error occurred during login. Please try again.", "danger")
            return render_template("auth/login.html", form=form), 500

    return render_template("auth/login.html", form=form)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = SignupForm()

    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()

        try:
            existing_user = User.query.filter_by(email=email).first()

            if existing_user:
                flash("An account with that email already exists.", "danger")
                return render_template("auth/signup.html", form=form), 400

            user = User(
                email=email,
                full_name=(form.full_name.data or "").strip(),
            )

            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            flash("Account created successfully. Please log in.", "success")

            return redirect(url_for("auth.login"))

        except Exception as exc:
            db.session.rollback()
            flash("A database error occurred during signup. Please try again.", "danger")
            return render_template("auth/signup.html", form=form), 500

    return render_template("auth/signup.html", form=form)



@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()

    flash("You have been signed out.", "success")

    return redirect(url_for("auth.login"))
# -*- coding: utf-8 -*-
"""Karnataka Explore - application factory.

Run locally:  python app.py      (http://127.0.0.1:5000)
"""
import os

from flask import Flask, render_template, request, session

import db as database
import i18n
from config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    database.init_app(app)
    i18n.init_app(app)

    from blueprints.public import bp as public_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.booking import bp as booking_bp
    from blueprints.admin import bp as admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # ---------------- template helpers ----------------
    @app.template_filter("money")
    def money(value):
        try:
            return "₹{:,.0f}".format(float(value or 0))
        except (TypeError, ValueError):
            return "₹0"

    @app.template_filter("pipes")
    def pipes(value):
        if not value:
            return []
        return [p.strip() for p in str(value).split("|") if p.strip()]

    @app.template_filter("stars")
    def stars(value):
        try:
            n = int(round(float(value or 0)))
        except (TypeError, ValueError):
            n = 0
        return "★" * n + "☆" * (5 - n)

    @app.template_filter("shortdate")
    def shortdate(value):
        if not value:
            return "-"
        return str(value)[:10]

    def page_url(page_number):
        from urllib.parse import urlencode
        args = request.args.to_dict(flat=True)
        args["page"] = page_number
        return request.path + "?" + urlencode(args)

    @app.context_processor
    def inject_globals():
        return {
            "site_name": app.config["SITE_NAME"],
            "site_tagline": app.config["SITE_TAGLINE"],
            "contact_email": app.config["CONTACT_EMAIL"],
            "contact_phone": app.config["CONTACT_PHONE"],
            "current_year": __import__("datetime").date.today().year,
            "logged_in": bool(session.get("user_id")),
            "user_name": session.get("user_name"),
            "admin_logged_in": bool(session.get("admin_id")),
            "admin_name": session.get("admin_name"),
            "current_path": request.path,
            "page_url": page_url,
        }

    # ---------------- error pages ----------------
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))

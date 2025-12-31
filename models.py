from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    capital = db.Column(db.Float, default=1000.0)

    trades = db.relationship('Trade', backref='user', lazy=True)
    portfolios = db.relationship('Portfolio', backref='user', lazy=True)  # Nouveau

    checklist_rules = db.relationship('ChecklistRule', backref='user', lazy=True)
    checklists = db.relationship('Checklist', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    capital = db.Column(db.Float, default=0.0)  # Capital propre au portefeuille
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trades = db.relationship('Trade', backref='portfolio', lazy=True)

class Trade(db.Model):
    __tablename__ = 'trade'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=True)  # Nouveau champ
    symbol = db.Column(db.String(32), nullable=False)
    entry = db.Column(db.Float, nullable=False)
    exit = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)
    pnl = db.Column(db.Float, nullable=True)
    lot = db.Column(db.Float, default=0.0)
    result = db.Column(db.String(10), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    risk = db.Column(db.Float)
    risk_reward = db.Column(db.Float)
    graph_link = db.Column(db.String(300))
    position_count = db.Column(db.Integer, default=1)
    comment = db.Column(db.Text, nullable=True)

class Publicite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    date_pub = db.Column(db.DateTime, default=datetime.utcnow)

class PubVue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pub_id = db.Column(db.Integer, db.ForeignKey('publicite.id'))

class Checklist(db.Model):
    __tablename__ = 'checklist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_rules = db.Column(db.Integer, nullable=False)
    respected_rules = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.String(255))

class ChecklistRule(db.Model):
    __tablename__ = 'checklist_rule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    checked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChecklistRule id={self.id} text={self.text[:30]!r}>"

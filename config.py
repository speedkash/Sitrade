import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Clé secrète (à changer avant mise en ligne)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'speedfint_secret_key'

    # Base de données SQLite locale
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'speedfint.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuration du mode debug
    DEBUG = True

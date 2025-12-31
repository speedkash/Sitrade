import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Clé secrète
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'speedfint_secret_key'

    # --- DÉBUT DE LA CORRECTION CRITIQUE ---
    # 1. Prend l'URL de la base depuis la variable d'environnement (Render)
    database_url = os.environ.get('DATABASE_URL')
    
    # 2. Si on est sur Render (URL existe), on l'utilise et on corrige le préfixe.
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = database_url
    # 3. Sinon, on utilise SQLite en développement local
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'speedfint.db')
    # --- FIN DE LA CORRECTION ---

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False  # Mettre False en production sur Render

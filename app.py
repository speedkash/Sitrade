from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Trade
from money_management import calculate_lot_size
from config import Config
from models import db, User, Trade, ChecklistRule, Checklist
from models import db, Publicite, PubVue

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        capital = float(request.form.get('capital', 1000))

        if User.query.filter_by(username=username).first():
            flash('Nom déjà utilisé')
            return redirect(url_for('register'))

        user = User(username=username, capital=capital)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Compte créé avec succès ! Connectez-vous.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # utilise la méthode du modèle
            session['user_id'] = user.id
            flash('Connexion réussie !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d’utilisateur ou mot de passe incorrect', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Déconnecté avec succès.', 'info')
    return redirect(url_for('index'))

from datetime import date
from flask import render_template, session, redirect, url_for
from models import User, Trade, Portfolio
from sqlalchemy import func

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    pub = Publicite.query.order_by(Publicite.date_pub.desc()).first()
    pub_vue = None
    if pub:
        pub_vue = PubVue.query.filter_by(user_id=user.id, pub_id=pub.id).first()

    # --- Récupération des portfolios de l'utilisateur ---
    portfolios = Portfolio.query.filter_by(user_id=user.id).order_by(Portfolio.name).all()

    # --- Gestion de la sélection du portfolio avec persistance session ---
    portfolio_id = request.args.get('portfolio_id', type=int)
    
    # Si un portfolio_id est passé dans l'URL, mettre à jour la session
    if portfolio_id:
        session['selected_portfolio_id'] = portfolio_id
    # Sinon, récupérer depuis la session
    elif 'selected_portfolio_id' in session:
        portfolio_id = session['selected_portfolio_id']
    
    selected_portfolio = None
    if portfolio_id:
        selected_portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first()
        # Si le portfolio n'existe plus (supprimé), nettoyer la session
        if not selected_portfolio and 'selected_portfolio_id' in session:
            session.pop('selected_portfolio_id')
            portfolio_id = None

    # --- Filtrage des trades selon le portefeuille sélectionné ---
    if selected_portfolio:
        trades = Trade.query.filter_by(user_id=user.id, portfolio_id=selected_portfolio.id)\
                            .order_by(Trade.date.desc()).limit(10).all()  # Augmenté à 10 pour mieux voir
    else:
        trades = Trade.query.filter_by(user_id=user.id).order_by(Trade.date.desc()).limit(10).all()

    # --- Calcul des stats ---
    if selected_portfolio:
        base_capital = selected_portfolio.capital
        all_trades = Trade.query.filter_by(user_id=user.id, portfolio_id=selected_portfolio.id).order_by(Trade.date.asc()).all()
    else:
        # Utiliser le capital utilisateur et tous les trades si pas de portfolio sélectionné
        base_capital = user.capital
        all_trades = Trade.query.filter_by(user_id=user.id).order_by(Trade.date.asc()).all()

    total_trades = len(all_trades)
    wins = len([t for t in all_trades if t.result == 'win'])
    losses = len([t for t in all_trades if t.result == 'loss'])
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    total_profit = sum(t.pnl for t in all_trades if t.result == 'win')
    total_loss = sum(abs(t.pnl) for t in all_trades if t.result == 'loss')
    net_profit = total_profit - total_loss

    profit_factor = round(total_profit / total_loss, 2) if total_loss > 0 else "∞"

    # --- Max Drawdown ---
    balance = base_capital
    peak = base_capital
    max_drawdown = 0
    for t in all_trades:
        balance += t.pnl
        peak = max(peak, balance)
        drawdown = ((peak - balance) / peak) * 100 if peak > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)

    # --- Capital actuel et pourcentage journalier ---
    current_capital = base_capital + net_profit
    today_trades = [t for t in all_trades if t.date.date() == date.today()]
    daily_profit = sum(t.pnl for t in today_trades)
    daily_percentage = round((daily_profit / base_capital) * 100, 2) if base_capital > 0 else 0

    stats = {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_profit': round(total_profit, 2),
        'total_loss': round(total_loss, 2),
        'net_profit': round(net_profit, 2),
        'profit_factor': profit_factor,
        'max_drawdown': round(max_drawdown, 2),
        'daily_percentage': daily_percentage
    }

    return render_template('dashboard.html',
                           user=user,
                           pub=pub,
                           pub_vue=pub_vue,
                           portfolios=portfolios,
                           selected_portfolio=selected_portfolio,
                           trades=trades,
                           stats=stats,
                           current_capital=round(current_capital, 2))

@app.route('/clear-portfolio')
def clear_portfolio():
    """Effacer la sélection du portfolio de la session"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Effacer la sélection de la session
    if 'selected_portfolio_id' in session:
        session.pop('selected_portfolio_id')
    
    flash('Sélection du portfolio effacée', 'info')
    return redirect(url_for('dashboard'))

from flask import request, flash, redirect, url_for, render_template, session
from models import Trade, Portfolio, User, db

@app.route('/add_trade', methods=['GET', 'POST'])
def add_trade():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    portfolios = Portfolio.query.filter_by(user_id=user.id).all()

    if request.method == 'POST':
        symbol = request.form['symbol']
        entry = float(request.form['entry'])
        exit_price = float(request.form['exit'])
        lot = float(request.form['lot_size'])
        risk = float(request.form.get('risk', 0))
        risk_reward = float(request.form.get('risk_reward', 0))
        graph_link = request.form.get('graph_link')
        position_count = int(request.form.get('position_count', 1))
        result = request.form.get('result')  # "win" ou "loss"
        portfolio_id = request.form.get('portfolio_id')
        comment=request.form.get("comment")

        # Gestion du portefeuille
        portfolio_id = int(portfolio_id) if portfolio_id else None

        # 💰 Calcul automatique du PnL
        # Si Win : PnL = risque * risk_reward * nombre de positions
        # Si Loss : PnL = -risque * nombre de positions
        if result == 'win':
            pnl = risk * risk_reward * position_count
        else:
            pnl = -risk * position_count

        # Création du trade
        new_trade = Trade(
            user_id=user.id,
            portfolio_id=portfolio_id,
            symbol=symbol,
            entry=entry,
            exit=exit_price,
            lot=lot,
            risk=risk,
            risk_reward=risk_reward,
            graph_link=graph_link,
            position_count=position_count,
            pnl=pnl,
            result=result,
            comment=comment
        )

        db.session.add(new_trade)
        db.session.commit()

        flash(f"Trade ajouté avec succès ({'Gain' if result == 'win' else 'Perte'} : {pnl}$)", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_trade.html', portfolios=portfolios)

@app.route('/trade/<int:trade_id>')
def view_trade(trade_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Récupérer le trade spécifique
    trade = Trade.query.filter_by(id=trade_id, user_id=session['user_id']).first_or_404()
    
    # Récupérer les 50 derniers trades de l'utilisateur (limité pour performance)
    available_trades = Trade.query.filter_by(
        user_id=session['user_id']
    ).order_by(Trade.date.desc()).limit(50).all()

    return render_template('view_trade.html', 
                           trade=trade, 
                           available_trades=available_trades)

@app.route('/edit_trade/<int:trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    # Vérifier que l'utilisateur est connecté
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Récupérer le trade avec vérification de l'utilisateur
    trade = Trade.query.filter_by(id=trade_id, user_id=session['user_id']).first_or_404()

    if request.method == 'POST':
        # Récupérer les données du formulaire
        trade.symbol = request.form['symbol']
        trade.lot = float(request.form['lot'])
        trade.pnl = float(request.form['pnl'])
        trade.result = request.form['result']
        
        # Gérer les champs optionnels
        risk = request.form.get('risk')
        if risk:
            trade.risk = float(risk)
        else:
            trade.risk = None
            
        risk_reward = request.form.get('risk_reward')
        if risk_reward:
            trade.risk_reward = float(risk_reward)
        else:
            trade.risk_reward = None
            
        position_count = request.form.get('position_count')
        if position_count:
            trade.position_count = int(position_count)
        else:
            trade.position_count = 1
            
        comment = request.form.get('comment')
        if comment:
            trade.comment = comment
        else:
            trade.comment = None
        
        # Mettre à jour la date de modification
        trade.updated_at = datetime.utcnow()
        
        # Sauvegarder dans la base de données
        try:
            db.session.commit()
            flash('Trade modifié avec succès!', 'success')
            return redirect(url_for('view_trade', trade_id=trade.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'danger')
            return redirect(url_for('edit_trade', trade_id=trade.id))

    # Pour GET, afficher le formulaire avec les trades disponibles
    available_trades = Trade.query.filter_by(
        user_id=session['user_id']
    ).order_by(Trade.date.desc()).all()
    
    return render_template('edit_trade.html', 
                           trade=trade, 
                           available_trades=available_trades)

@app.route('/delete_trade/<int:trade_id>', methods=['POST'])
def delete_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    db.session.delete(trade)
    db.session.commit()
    return redirect(url_for('dashboard'))  # ou la page où tu affiches les trades

@app.route('/checklist', methods=['GET', 'POST'])
def checklist():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Si l'utilisateur soumet le formulaire (cochage + calcul du respect)
    if request.method == 'POST':
        checked_ids = request.form.getlist('rules')
        all_rules = ChecklistRule.query.filter_by(user_id=user.id).all()

        # Mettre à jour les règles cochées / décochées
        for rule in all_rules:
            rule.checked = str(rule.id) in checked_ids
        db.session.commit()

        # Calcul du respect total
        total = len(all_rules)
        respected = len(checked_ids)
        percentage = round((respected / total) * 100, 2) if total > 0 else 0

        if percentage >= 90:
            feedback = "✅ Excellente préparation ! Risque minimal, trade solide."
        elif percentage >= 70:
            feedback = "🟡 Bon setup, mais révise quelques points avant d'entrer."
        elif percentage >= 50:
            feedback = "⚠️ Préparation incomplète, revois ta stratégie avant d'entrer."
        else:
            feedback = "❌ Préparation insuffisante. Évite ce trade."

        return render_template('checklist_result.html', percentage=percentage, feedback=feedback)

    # Sinon : afficher la checklist personnelle
    rules = ChecklistRule.query.filter_by(user_id=user.id).all()
    return render_template('checklist.html', rules=rules)

@app.route('/add_rule', methods=['POST'])
def add_rule():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    text = request.form.get('text')
    if text:
        new_rule = ChecklistRule(user_id=session['user_id'], text=text)
        db.session.add(new_rule)
        db.session.commit()

    return redirect(url_for('checklist'))

@app.route('/update_capital', methods=['POST'])
def update_capital():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    new_capital = request.form.get('capital', type=float)
    user = User.query.get(session['user_id'])

    if new_capital is not None and new_capital >= 0:
        user.capital = new_capital
        db.session.commit()
        flash('Capital mis à jour avec succès ✅', 'success')
    else:
        flash('Valeur invalide', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/delete_all_trades', methods=['POST'])
def delete_all_trades():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    trades = Trade.query.filter_by(user_id=user_id).all()
    for trade in trades:
        db.session.delete(trade)
    db.session.commit()
    flash('Tous les trades ont été supprimés.', 'success')
    return redirect(url_for('dashboard'))

from flask import request, flash
from models import Portfolio, db

# Créer un portefeuille
@app.route('/create_portfolio', methods=['GET', 'POST'])
def create_portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        capital = float(request.form.get('capital', 1000))
        if name:
            new_portfolio = Portfolio(user_id=session['user_id'], name=name, capital=capital)
            db.session.add(new_portfolio)
            db.session.commit()
            flash('Portefeuille créé avec succès !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Le nom du portefeuille est requis.', 'danger')

    return render_template('create_portfolio.html')

@app.route('/delete_portfolio/<int:portfolio_id>', methods=['POST'])
def delete_portfolio(portfolio_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    portfolio = Portfolio.query.get_or_404(portfolio_id)

    # Vérifie que le portefeuille appartient bien à l'utilisateur
    if portfolio.user_id != session['user_id']:
        flash("Vous n'avez pas la permission de supprimer ce portefeuille.", "danger")
        return redirect(url_for('dashboard'))

    # Supprimer tous les trades liés au portefeuille
    Trade.query.filter_by(portfolio_id=portfolio.id).delete()

    # Supprimer le portefeuille lui-même
    db.session.delete(portfolio)
    db.session.commit()

    flash("Portefeuille et tous ses trades supprimés avec succès.", "success")
    return redirect(url_for('dashboard'))

@app.route("/marquer_pub_lue/<int:pub_id>")
def marquer_pub_lue(pub_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    deja_vue = PubVue.query.filter_by(user_id=user_id, pub_id=pub_id).first()
    if not deja_vue:
        vue = PubVue(user_id=user_id, pub_id=pub_id)
        db.session.add(vue)
        db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/admin/publicite", methods=["GET", "POST"])
def admin_publicite():
    if request.method == "POST":
        titre = request.form["titre"]
        description = request.form["description"]
        image_url = request.form["image_url"]

        pub = Publicite(titre=titre, description=description, image_url=image_url)
        db.session.add(pub)
        db.session.commit()
        flash("Publicité ajoutée avec succès !", "success")
        return redirect(url_for("admin_publicite"))

    pubs = Publicite.query.order_by(Publicite.date_pub.desc()).all()
    return render_template("admin_publicite.html", pubs=pubs)

from flask import render_template, redirect, url_for, flash
from models import User, Portfolio, Trade

@app.route('/admin/users')
def admin_users():

    # Récupère tous les utilisateurs
    users = User.query.order_by(User.id.asc()).all()

    # Précharge les portefeuilles et trades pour chaque utilisateur
    for user in users:
        user.portfolios = Portfolio.query.filter_by(user_id=user.id).all()
        user.trades = Trade.query.filter_by(user_id=user.id).all()

    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:user_id>/delete')
def admin_delete_user(user_id):

    user = User.query.get_or_404(user_id)
    # Supprime d'abord les trades et portefeuilles associés
    Trade.query.filter_by(user_id=user.id).delete()
    Portfolio.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("Utilisateur supprimé avec succès !", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>')
def admin_view_user(user_id):

    user = User.query.get_or_404(user_id)
    portfolios = Portfolio.query.filter_by(user_id=user.id).all()
    trades = Trade.query.filter_by(user_id=user.id).all()
    return render_template('admin_view_user.html', user=user, portfolios=portfolios, trades=trades)

from flask import render_template, session, redirect, url_for, request
from datetime import date, datetime
from models import Trade, User

@app.route('/journal')
def journal_trading():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # ---- RÉCUPÉRATION DES DATES ----
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Trade.query.filter_by(user_id=user.id)

    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Trade.date >= start)
        except:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            # ajouter fin de journée 23:59:59
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(Trade.date <= end)
        except:
            pass

    all_trades = query.order_by(Trade.date.asc()).all()

    # ---- TON CALCUL ORIGINAL ----
    base_capital = 1000
    total_trades = len(all_trades)
    wins = sum(1 for t in all_trades if t.result == 'win')
    losses = sum(1 for t in all_trades if t.result == 'loss')
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    total_profit = sum(t.pnl for t in all_trades if t.pnl > 0)
    total_loss = sum(abs(t.pnl) for t in all_trades if t.pnl < 0)
    net_profit = total_profit - total_loss
    profit_factor = round(total_profit / total_loss, 2) if total_loss > 0 else float('inf')

    # Drawdown
    max_drawdown = 0
    peak = 0
    running_sum = 0
    for trade in all_trades:
        running_sum += trade.pnl
        if running_sum > peak:
            peak = running_sum
        drawdown = peak - running_sum
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    current_capital = base_capital + net_profit

    # Stats du jour (adapté si filtre appliqué)
    today_trades = [t for t in all_trades if t.date.date() == date.today()]
    daily_profit = sum(t.pnl for t in today_trades)
    daily_percentage = round((daily_profit / current_capital) * 100, 2) if current_capital > 0 else 0

    # Graphiques
    dates = [t.date.strftime('%d/%m') for t in all_trades]
    pnl_data = []
    cumulative = 0
    for trade in all_trades:
        cumulative += trade.pnl
        pnl_data.append(cumulative)

    stats = {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_profit': round(total_profit, 2),
        'total_loss': round(total_loss, 2),
        'net_profit': round(net_profit, 2),
        'profit_factor': profit_factor,
        'max_drawdown': round(max_drawdown, 2),
        'daily_percentage': daily_percentage
    }

    # Afficher les 10 derniers trades (ou filtrés)
    trades = all_trades[-10:]

    return render_template(
        'journal.html',
        user=user,
        trades=trades,
        stats=stats,
        current_capital=round(current_capital, 2),
        base_capital=base_capital,
        dates=dates,
        pnl_data=pnl_data
    )

if __name__ == '__main__':
    app.run(debug=True, port=5005)

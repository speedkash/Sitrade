import re
from datetime import datetime
from app import app, db
from models import Trade, User

def extract_trades_from_text(text):
    """
    Extrait les trades depuis le texte OCR brut
    Exemple de lignes :
    EURJPY, sell 1.50
    178.170 - 178.392
    """
    trades = []
    pattern_symbol = re.compile(r"([A-Z]{3,7}),\s*(buy|sell)\s*([\d\.]+)", re.IGNORECASE)
    pattern_prices = re.compile(r"([\d\.]+)\s*[-–]\s*([\d\.]+)")

    lines = text.splitlines()
    for i in range(len(lines)):
        match_symbol = pattern_symbol.search(lines[i])
        if match_symbol and i + 1 < len(lines):
            symbol, direction, lot = match_symbol.groups()
            match_price = pattern_prices.search(lines[i + 1])
            if match_price:
                entry, exit_price = map(float, match_price.groups())

                pnl = (exit_price - entry) * float(lot) * 100
                if direction.lower() == 'sell':
                    pnl *= -1
                result = 'win' if pnl > 0 else 'loss'

                trades.append({
                    "symbol": symbol.upper(),
                    "direction": direction.lower(),
                    "lot": float(lot),
                    "entry": entry,
                    "exit": exit_price,
                    "pnl": round(pnl, 2),
                    "result": result
                })
    return trades


def save_trades_to_db(user_id, trades):
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print("Utilisateur introuvable !")
            return

        for t in trades:
            trade = Trade(
                user_id=user.id,
                symbol=t["symbol"],
                entry=t["entry"],
                exit=t["exit"],
                pnl=t["pnl"],
                result=t["result"],
                date=datetime.now()
            )
            db.session.add(trade)
            user.capital += t["pnl"]
        db.session.commit()
        print(f"{len(trades)} trades ajoutés pour {user.username}")


if __name__ == "__main__":
    with open("output.txt", "r", encoding="utf-8") as f:
        text = f.read()

    extracted_trades = extract_trades_from_text(text)
    print(f"Trades détectés : {len(extracted_trades)}")

    if extracted_trades:
        # Remplace 1 par l'ID utilisateur à qui tu veux attribuer les trades
        save_trades_to_db(user_id=1, trades=extracted_trades)

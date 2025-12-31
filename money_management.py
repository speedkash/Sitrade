# Calcul automatique du lot size selon le capital, le risque et le stop loss
def calculate_lot_size(capital, risk_percent, stop_loss_pips, pip_value=10):
    """
    capital: float, capital du compte
    risk_percent: float, pourcentage du capital à risquer (1 = 1%)
    stop_loss_pips: float, distance du stop loss en pips
    pip_value: valeur du pip pour 1 lot (simplifié)
    """
    risk_amount = capital * (risk_percent / 100)
    if stop_loss_pips <= 0:
        return 0
    lot = risk_amount / (stop_loss_pips * pip_value)
    return round(lot, 4)

# Calcul simple des statistiques utilisateur
def compute_stats(trades):
    total_trades = len(trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    losses = sum(1 for t in trades if t.pnl < 0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(t.pnl for t in trades if t.pnl > 0)
    total_loss = -sum(t.pnl for t in trades if t.pnl < 0)
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf') if total_profit > 0 else 0
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "profit_factor": round(profit_factor, 2)
    }

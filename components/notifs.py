def get_notif_solde(user_info):
    notifs = []
    try:
        solde = float(user_info['solde'])
        revenus = float(user_info['revenus'])

        ratio = 1 - (solde/revenus) if revenus > 0 else 0

        if ratio > 0.7:
            notifs.append({
                "type": "⚠️ Alerte de Solde",
                "message": "Vous avez consommé "
                f"{ratio:.0%} de vos revenus mensuels. Pensez à modérer "
                "vos dépenses."
            })
    except (ValueError, KeyError):
        pass

    return notifs

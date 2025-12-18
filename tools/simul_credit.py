from langchain.tools import tool


# --- Tool Definition ---
@tool
def simul_credit(revenus: int, montant: int, duree: int):
    """Trouve si un crédit est réalisable en fonction des revenus,
    du montant et de la durée, en respectant la quotité cessible de 42%.
    revenus: revenus mensuels
    montant: montant du crédit
    duree: durée du crédit en années
    Retourne un message indiquant si le crédit est réalisable ou non.
    """
    # 1. Define Variables
    tx_interet = 0.035          # 3.5% Annual Interest
    tx_assurance = 0.011        # 1.1% Annual Insurance (on Capital)
    tx_tps = 0.10               # 10% Tax (TOB) on Interest + Insurance
    nbr_paiements = duree * 12

    # 2. Monthly Rates
    mensualite_taux = tx_interet / 12
    assurance_mensuelle = (montant * tx_assurance) / 12

    # 3. Base Monthly Payment (Principal + Interest)
    # Standard amortization formula
    if mensualite_taux > 0:
        denominator = 1 - (1 + mensualite_taux) ** -nbr_paiements
        mensualite_base = (montant * mensualite_taux) / denominator
    else:
        mensualite_base = montant / nbr_paiements

    # 4. Tax Calculation (TPS/TOB)
    # Tax applies to the Interest portion (max at month 1) + Insurance
    interet_premier_mois = montant * mensualite_taux
    taxe_mensuelle = (interet_premier_mois + assurance_mensuelle) * tx_tps

    # 5. Total Monthly Payment (Conservative Estimate)
    mensualite = mensualite_base + assurance_mensuelle + taxe_mensuelle

    # 6. Checks (Quotité Cessible 42%)
    quot_cessible = revenus * 0.42

    if mensualite > quot_cessible:
        return (f"Le montant de la mensualité : {mensualite:.2f}, "
                "dépasse la quotité cessible : "
                f"{quot_cessible:.2f}. Crédit non réalisable.")
    else:
        return f"Crédit réalisable avec une mensualité de {mensualite:.2f}"

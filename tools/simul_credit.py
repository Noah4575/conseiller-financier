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


@tool
def simul_credit_immo(revenus: int, montant: int, duree: int):
    """Trouve si un crédit immobilier est réalisable en fonction des revenus,
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

    PALIERS_FRAIS_DOSSIER = [
        {
            "min_pret": 5_000_000,
            "max_pret": 25_000_000,
            "taux_ht": 0.015,
            "min_frais_ttc": 0,
            "max_frais_ttc": 200_000
        },
        {
            "min_pret": 25_000_001,
            "max_pret": 50_000_000,
            "taux_ht": 0.015,
            "min_frais_ttc": 0,
            "max_frais_ttc": 300_000
        },
        {
            "min_pret": 50_000_001,
            "max_pret": 100_000_000,
            "taux_ht": 0.015,
            "min_frais_ttc": 0,
            "max_frais_ttc": 500_000
        },
        {
            "min_pret": 100_000_001,
            "max_pret": float('inf'),
            "taux_ht": 0.0075,
            "min_frais_ttc": 750_000,
            "max_frais_ttc": 3_000_000
        }
    ]

    palier = next(
        (p for p in PALIERS_FRAIS_DOSSIER
         if p["min_pret"] <= montant <= p["max_pret"]),
        None
    )

    if palier:
        frais_ht = montant * palier["taux_ht"]
        frais_ttc = frais_ht * (1 + tx_tps)

        frais = max(palier["min_frais_ttc"], min(frais_ttc,
                                                 palier["max_frais_ttc"]))

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
        return (f"Crédit réalisable avec mensualité de {mensualite:.2f} FCFA"
                f"et des frais de dossier de {frais:,.2f} FCFA.")


@tool
def simul_emprunt_max(revenus: int, duree: int):
    """
    Calcule le montant total maximal qu'un client peut emprunter en fonction de
    ses revenus et de la durée, en respectant la quotité cessible de 42%.
    revenus: revenus mensuels nets
    duree: durée du crédit en années
    """
    # 1. Constantes (identiques à simul_credit)
    tx_interet_annuel = 0.035
    tx_assurance_annuel = 0.011
    tx_tps = 0.10
    nbr_paiements = duree * 12

    # 2. Mensualité maximale autorisée (42%)
    mensualite_max = revenus * 0.42

    m_r = tx_interet_annuel / 12
    ass_m = tx_assurance_annuel / 12

    # Facteur pour la mensualité de base (amortissement)
    if m_r > 0:
        f_base = m_r / (1 - (1 + m_r) ** -nbr_paiements)
    else:
        f_base = 1 / nbr_paiements

    # Facteur pour l'assurance et la taxe
    f_assurance = ass_m
    f_taxe = (m_r + ass_m) * tx_tps

    # Facteur total
    K = f_base + f_assurance + f_taxe

    # 4. Calcul du Capital Maximal
    montant_max = mensualite_max / K

    return (f"Basé sur vos revenus de {revenus:,} FCFA et une durée de {duree}"
            "ans :\n"
            f"- Votre capacité de remboursement mensuelle est de :"
            f"{mensualite_max:,.0f} FCFA.\n"
            f"- Le montant total maximal que vous pouvez emprunter est estimé "
            f"à : **{montant_max:,.0f} FCFA**.")


@tool
def simul_epargne(versements : float, duree : int, cible : int):
    """
    Calcule la croissance d'une épargne avec des versements réguliers et des intérêts composés.
    """
    return None
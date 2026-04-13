from langchain.tools import tool
import difflib


# --- Tool Definition ---
@tool
def simul_dat(produit: str, montant: int, duree: int):
    """Simule un Dépôt à Terme (DAT) en fonction du montant et
     de la durée en mois.
    """
    # 1. Define Variables
    # On définit les bornes supérieures des paliers (en millions de FCFA)
    PALIERS_MONTANT = [1000000, 10000000, 50000000, 100000000, float('inf')]

    # On définit les bornes supérieures des maturités (en mois)
    PALIERS_DUREE = [3, 6, 12, 24, 36, 48, 60, float('inf')]

    GRILLE_TAUX_DAT = [
        [None, 0.0225, 0.0250, 0.0315],  # 3 à 6 mois
        [None, 0.0250, 0.0275, 0.0328],  # 6 à 12 mois
        [0.0200, 0.0275, 0.0300, 0.0340],  # 12 à 24 mois
        [0.0250, 0.0325, 0.0350, 0.0450],  # 24 à 36 mois
        [0.0350, 0.0400, 0.0450, 0.0475],  # 36 à 48 mois
        [0.0385, 0.0435, 0.0485, 0.0510],  # 48 à 60 mois
        [0.0410, 0.0460, 0.0510, 0.0510]  # 60 mois et plus
    ]

    for i, palier_montant in enumerate(PALIERS_MONTANT):
        if montant <= palier_montant:
            col = i-1
            break
    else:
        col = len(PALIERS_MONTANT) - 1

    for i, palier_duree in enumerate(PALIERS_DUREE):
        if duree <= palier_duree:
            row = i-1
            break
    else:
        row = len(PALIERS_DUREE) - 1

    taux = GRILLE_TAUX_DAT[row][col]

    if taux is None:
        return (f"Le produit '{produit}' n'est pas disponible pour un montant "
                f"de {montant} FCFA et une durée de {duree} mois. Veuillez "
                "augmenter le montant ou la durée pour procéder.")

    total = montant * (1+taux) ** (duree / 12)
    interets = total - montant

    return (f"Pour un {produit} de {montant:,} FCFA sur {duree} mois :\n"
            f"- Taux d'intérêt applicable : {taux*100:.2f}%\n"
            f"- Intérêts générés : {interets:,.0f} FCFA\n"
            f"- Montant total à l'échéance : {total:,.0f} FCFA")


# --- Tool Definition ---
@tool
def simul_car8(produit: str, montant: int, frequence: str):
    """Simule un Dépôt à Terme (DAT) en fonction du montant
     et de la durée en mois.
    """
    # 1. Define Variables
    # On définit les bornes (en millions de FCFA)
    PALIERS_MONTANT = [5000000, 5000000000]
    TAUX_HT = 0.05
    duree = 96
    options_valides = ["mensuelle", "trimestrielle", "semestrielle",
                       "annuelle"]

    # Trouve le mot le plus proche parmi les options valides
    proche = difflib.get_close_matches(frequence.lower(), options_valides,
                                       n=1, cutoff=0.6)

    # Si on a trouvé un match, on l'utilise, sinon par défaut trimestrielle
    freq_final = proche[0] if proche else "trimestrielle"

    mapping = {"mensuelle": 12, "trimestrielle": 4, "semestrielle": 2,
               "annuelle": 1}
    periode = mapping[freq_final]

    if montant > PALIERS_MONTANT[1] or montant < PALIERS_MONTANT[0]:
        return (f"Le produit '{produit}' n'est pas disponible pour un montant "
                f"de {montant} FCFA. Veuillez choisir un montant entre "
                f"{PALIERS_MONTANT[0]:,} FCFA et {PALIERS_MONTANT[1]:,} FCFA.")

    else:
        interets_dist = montant * (TAUX_HT / periode)
        interets_dist_total = interets_dist * (periode * 8)
        total_dist = montant + interets_dist_total

        total_cap = montant * (1 + TAUX_HT)**(duree / 12)
        interets_cap = total_cap - montant

        return (f"Pour un {produit} de {montant:,} FCFA sur {duree} mois :\n"
                f"- Si intérêts capitalisés: {interets_cap:,.0f} FCFA\n"
                f"  Montant total à l'échéance : {total_cap:,.0f} FCFA\n"
                f"- Si les intérêts sont distribués de manière {freq_final} : "
                f"{interets_dist:,.0f} FCFA\n"
                f"  Montant total à l'échéance : {total_dist:,.0f} FCFA\n")


@tool
def simul_pel(produit: str, depot_init: int, depot_mensuel: int,
              duree: int):
    """Simule un Plan d'Épargne Logement (PEL) en fonction de la duree
    """
    depot_init_min = 50000
    depot_mensuel_min = 25000
    taux = 0.035
    PALIERS_DUREE = [36, 120]

    if duree < PALIERS_DUREE[0] or duree > PALIERS_DUREE[1]:
        return (f"Le produit '{produit}' n'est pas disponible pour une durée "
                f"de {duree} mois. Veuillez choisir une durée entre "
                f"{PALIERS_DUREE[0]} mois et {PALIERS_DUREE[1]} mois.")

    if depot_init < depot_init_min or depot_mensuel < depot_mensuel_min:
        return (f"Le produit '{produit}' n'est pas disponible pour un dépôt "
                f"initial de {depot_init} FCFA ou un dépôt mensuel de "
                f"{depot_mensuel} FCFA. Veuillez choisir un dépôt initial "
                f"supérieur à {depot_init_min} FCFA et un dépôt mensuel "
                f"supérieur à {depot_mensuel_min} FCFA.")

    else:
        total_depots = depot_init + depot_mensuel * duree
        interets = total_depots * taux * (duree / 12)
        total = total_depots + interets

        return (f"Pour un {produit} sur {duree} mois :\n"
                f"- Total des dépôts : {total_depots:,.0f} FCFA\n"
                f"- Intérêts générés : {interets:,.0f} FCFA\n"
                f"- Montant total à l'échéance : {total:,.0f} FCFA\n")


@tool
def simul_credimatic(produit: str, depot_init: int, depot_mensuel: int,
                     duree: int):
    """Simule un Plan d'Épargne Logement (PEL) en fonction de la duree
    """
    depot_init_min = 25000
    depot_mensuel_min = 10000
    montant_max = 5000000
    taux = 0.035
    PALIERS_DUREE = [12, 24]

    if duree < PALIERS_DUREE[0] or duree > PALIERS_DUREE[1]:
        return (f"Le produit '{produit}' n'est pas disponible pour une durée "
                f"de {duree} mois. Veuillez choisir une durée entre "
                f"{PALIERS_DUREE[0]} mois et {PALIERS_DUREE[1]} mois.")

    if depot_init < depot_init_min or depot_mensuel < depot_mensuel_min:
        return (f"Le produit '{produit}' n'est pas disponible pour un dépôt "
                f"initial de {depot_init} FCFA ou un dépôt mensuel de "
                f"{depot_mensuel} FCFA. Veuillez choisir un dépôt initial "
                f"supérieur à {depot_init_min} FCFA et un dépôt mensuel "
                f"supérieur à {depot_mensuel_min} FCFA.")

    else:
        total_depots = depot_init + depot_mensuel * duree
        if total_depots > montant_max:
            return (f"Le produit '{produit}' n'est pas disponible pour un "
                    f"montant total de dépôts de {total_depots:,.0f} FCFA. "
                    f"Veuillez choisir des dépôts inférieurs à {
                        montant_max:,.0f} FCFA.")

        interets = total_depots * taux * (duree / 12)
        total = total_depots + interets

        return (f"Pour un {produit} sur {duree} mois :\n"
                f"- Total des dépôts : {total_depots:,.0f} FCFA\n"
                f"- Intérêts générés : {interets:,.0f} FCFA\n"
                f"- Montant total à l'échéance : {total:,.0f} FCFA\n")


@tool
def simul_sogeprimo(produit: str, depot_init: int, depot_mensuel: int,
                    age: int):
    """Simule un Compte d'Épargne Sogeprimo pour un mineur, en fonction de son
    âge.
    """
    depot_mensuel_min = 5000
    montant_max = 10000000
    taux = 0.035
    duree_max = 216

    if age >= duree_max:
        return (f"Le produit '{produit}' n'est pas disponible pour une "
                f"personne de cet age. Elle doit être âgée de moins de "
                "18 ans pour pouvoir souscrire à ce produit.")

    if depot_mensuel < depot_mensuel_min:
        return (f"Le produit '{produit}' n'est pas disponible pour un "
                f"dépôt mensuel de {depot_mensuel} FCFA. Veuillez choisir "
                f"un dépôt mensuel supérieur à {depot_mensuel_min} FCFA.")

    else:
        duree = duree_max - age
        total_depots = depot_init + depot_mensuel * duree
        if total_depots > montant_max:
            return (f"Le produit '{produit}' n'est pas disponible pour un "
                    f"montant total de dépôts de {total_depots:,.0f} FCFA. "
                    "Veuillez choisir des dépôts inférieurs à "
                    f"{montant_max:,.0f} FCFA.")

        interets = total_depots * taux * (duree / 12)
        total = total_depots + interets

        return (f"Pour un {produit} sur {duree} mois :\n"
                f"- Total des dépôts : {total_depots:,.0f} FCFA\n"
                f"- Intérêts générés : {interets:,.0f} FCFA\n"
                f"- Montant total à l'échéance : {total:,.0f} FCFA\n")

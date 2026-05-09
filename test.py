import json
import random
from datetime import datetime, timedelta

random.seed(42)

# ── Data pools ────────────────────────────────────────────────────────────────

BRANDS = {
    "Toyota": {
        "country": "Japan", "founded": 1937, "type": "mass_market",
        "models": [
            {"name": "Yaris", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "Corolla", "type": "berline", "body": "sedan", "segment": "C"},
            {"name": "Camry", "type": "berline", "body": "sedan", "segment": "D"},
            {"name": "RAV4", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Land Cruiser", "type": "suv", "body": "suv", "segment": "E-SUV"},
            {"name": "C-HR", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "Highlander", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "Prius", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "GR86", "type": "sport", "body": "coupe", "segment": "Sport"},
            {"name": "Hilux", "type": "pickup", "body": "pickup", "segment": "Pickup"},
        ]
    },
    "BMW": {
        "country": "Germany", "founded": 1916, "type": "premium",
        "models": [
            {"name": "Série 1", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "Série 3", "type": "berline", "body": "sedan", "segment": "D"},
            {"name": "Série 5", "type": "berline", "body": "sedan", "segment": "E"},
            {"name": "Série 7", "type": "berline", "body": "sedan", "segment": "F"},
            {"name": "X1", "type": "suv", "body": "suv", "segment": "B-SUV"},
            {"name": "X3", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "X5", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "M3", "type": "sport", "body": "sedan", "segment": "Sport"},
            {"name": "M4", "type": "sport", "body": "coupe", "segment": "Sport"},
            {"name": "iX", "type": "electrique", "body": "suv", "segment": "E-SUV"},
        ]
    },
    "Mercedes-Benz": {
        "country": "Germany", "founded": 1926, "type": "premium",
        "models": [
            {"name": "Classe A", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "Classe C", "type": "berline", "body": "sedan", "segment": "D"},
            {"name": "Classe E", "type": "berline", "body": "sedan", "segment": "E"},
            {"name": "Classe S", "type": "berline", "body": "sedan", "segment": "F"},
            {"name": "GLA", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "GLC", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "GLE", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "AMG GT", "type": "sport", "body": "coupe", "segment": "Sport"},
            {"name": "EQS", "type": "electrique", "body": "sedan", "segment": "F"},
            {"name": "EQC", "type": "electrique", "body": "suv", "segment": "C-SUV"},
        ]
    },
    "Peugeot": {
        "country": "France", "founded": 1882, "type": "mass_market",
        "models": [
            {"name": "208", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "308", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "508", "type": "berline", "body": "sedan", "segment": "E"},
            {"name": "2008", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "3008", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "5008", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "e-208", "type": "electrique", "body": "hatchback", "segment": "B"},
            {"name": "e-2008", "type": "electrique", "body": "crossover", "segment": "B-SUV"},
            {"name": "Rifter", "type": "monospace", "body": "van", "segment": "MPV"},
            {"name": "Traveller", "type": "monospace", "body": "van", "segment": "MPV"},
        ]
    },
    "Volkswagen": {
        "country": "Germany", "founded": 1937, "type": "mass_market",
        "models": [
            {"name": "Polo", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "Golf", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "Passat", "type": "berline", "body": "sedan", "segment": "E"},
            {"name": "Tiguan", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Touareg", "type": "suv", "body": "suv", "segment": "E-SUV"},
            {"name": "T-Roc", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "ID.3", "type": "electrique", "body": "hatchback", "segment": "C"},
            {"name": "ID.4", "type": "electrique", "body": "suv", "segment": "C-SUV"},
            {"name": "Golf GTI", "type": "sport", "body": "hatchback", "segment": "Sport"},
            {"name": "Arteon", "type": "berline", "body": "fastback", "segment": "E"},
        ]
    },
    "Ferrari": {
        "country": "Italy", "founded": 1939, "type": "supercar",
        "models": [
            {"name": "Roma", "type": "sport", "body": "coupe", "segment": "GT"},
            {"name": "Portofino M", "type": "sport", "body": "cabriolet", "segment": "GT"},
            {"name": "F8 Tributo", "type": "sport", "body": "coupe", "segment": "Supercar"},
            {"name": "SF90 Stradale", "type": "hybride", "body": "coupe", "segment": "Hypercar"},
            {"name": "812 Superfast", "type": "sport", "body": "coupe", "segment": "GT"},
            {"name": "Purosangue", "type": "suv", "body": "suv", "segment": "Luxury-SUV"},
        ]
    },
    "Renault": {
        "country": "France", "founded": 1899, "type": "mass_market",
        "models": [
            {"name": "Clio", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "Mégane", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "Talisman", "type": "berline", "body": "sedan", "segment": "E"},
            {"name": "Captur", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "Kadjar", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Koleos", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "Zoe", "type": "electrique", "body": "hatchback", "segment": "B"},
            {"name": "Arkana", "type": "suv", "body": "crossover", "segment": "C-SUV"},
            {"name": "Kangoo", "type": "monospace", "body": "van", "segment": "MPV"},
            {"name": "Austral", "type": "suv", "body": "suv", "segment": "C-SUV"},
        ]
    },
    "Tesla": {
        "country": "USA", "founded": 2003, "type": "electrique",
        "models": [
            {"name": "Model 3", "type": "electrique", "body": "sedan", "segment": "D"},
            {"name": "Model S", "type": "electrique", "body": "sedan", "segment": "F"},
            {"name": "Model X", "type": "electrique", "body": "suv", "segment": "E-SUV"},
            {"name": "Model Y", "type": "electrique", "body": "suv", "segment": "C-SUV"},
            {"name": "Cybertruck", "type": "electrique", "body": "pickup", "segment": "Pickup"},
        ]
    },
    "Audi": {
        "country": "Germany", "founded": 1909, "type": "premium",
        "models": [
            {"name": "A1", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "A3", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "A4", "type": "berline", "body": "sedan", "segment": "D"},
            {"name": "A6", "type": "berline", "body": "sedan", "segment": "E"},
            {"name": "A8", "type": "berline", "body": "sedan", "segment": "F"},
            {"name": "Q3", "type": "suv", "body": "suv", "segment": "B-SUV"},
            {"name": "Q5", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Q7", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "e-tron", "type": "electrique", "body": "suv", "segment": "D-SUV"},
            {"name": "RS6", "type": "sport", "body": "break", "segment": "Sport"},
        ]
    },
    "Hyundai": {
        "country": "South Korea", "founded": 1967, "type": "mass_market",
        "models": [
            {"name": "i10", "type": "citadine", "body": "hatchback", "segment": "A"},
            {"name": "i20", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "i30", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "Tucson", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Santa Fe", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "Kona", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "Ioniq 5", "type": "electrique", "body": "crossover", "segment": "C-SUV"},
            {"name": "Ioniq 6", "type": "electrique", "body": "sedan", "segment": "D"},
            {"name": "Nexo", "type": "hydrogene", "body": "suv", "segment": "C-SUV"},
            {"name": "Elantra", "type": "berline", "body": "sedan", "segment": "C"},
        ]
    },
    "Lamborghini": {
        "country": "Italy", "founded": 1963, "type": "supercar",
        "models": [
            {"name": "Huracán", "type": "sport", "body": "coupe", "segment": "Supercar"},
            {"name": "Urus", "type": "suv", "body": "suv", "segment": "Luxury-SUV"},
            {"name": "Revuelto", "type": "hybride", "body": "coupe", "segment": "Hypercar"},
        ]
    },
    "Kia": {
        "country": "South Korea", "founded": 1944, "type": "mass_market",
        "models": [
            {"name": "Picanto", "type": "citadine", "body": "hatchback", "segment": "A"},
            {"name": "Ceed", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "Sportage", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Sorento", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "EV6", "type": "electrique", "body": "crossover", "segment": "C-SUV"},
            {"name": "EV9", "type": "electrique", "body": "suv", "segment": "D-SUV"},
            {"name": "Stinger", "type": "sport", "body": "fastback", "segment": "Sport"},
            {"name": "Niro", "type": "hybride", "body": "crossover", "segment": "B-SUV"},
        ]
    },
    "Ford": {
        "country": "USA", "founded": 1903, "type": "mass_market",
        "models": [
            {"name": "Fiesta", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "Focus", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "Mustang", "type": "sport", "body": "coupe", "segment": "Sport"},
            {"name": "Puma", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "Kuga", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Explorer", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "Mustang Mach-E", "type": "electrique", "body": "suv", "segment": "C-SUV"},
            {"name": "F-150 Lightning", "type": "electrique", "body": "pickup", "segment": "Pickup"},
        ]
    },
    "Porsche": {
        "country": "Germany", "founded": 1931, "type": "premium",
        "models": [
            {"name": "911", "type": "sport", "body": "coupe", "segment": "Sport"},
            {"name": "Cayenne", "type": "suv", "body": "suv", "segment": "D-SUV"},
            {"name": "Macan", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "Panamera", "type": "berline", "body": "fastback", "segment": "F"},
            {"name": "Taycan", "type": "electrique", "body": "sedan", "segment": "E"},
            {"name": "718 Cayman", "type": "sport", "body": "coupe", "segment": "Sport"},
        ]
    },
    "Citroën": {
        "country": "France", "founded": 1919, "type": "mass_market",
        "models": [
            {"name": "C1", "type": "citadine", "body": "hatchback", "segment": "A"},
            {"name": "C3", "type": "citadine", "body": "hatchback", "segment": "B"},
            {"name": "C4", "type": "berline", "body": "hatchback", "segment": "C"},
            {"name": "C5 X", "type": "berline", "body": "crossover", "segment": "D"},
            {"name": "C3 Aircross", "type": "suv", "body": "crossover", "segment": "B-SUV"},
            {"name": "C5 Aircross", "type": "suv", "body": "suv", "segment": "C-SUV"},
            {"name": "ë-C4", "type": "electrique", "body": "hatchback", "segment": "C"},
            {"name": "Berlingo", "type": "monospace", "body": "van", "segment": "MPV"},
        ]
    },
}

FUEL_TYPES = {
    "essence": {"co2_factor": 1.0, "consumption_factor": 1.0},
    "diesel": {"co2_factor": 1.15, "consumption_factor": 0.75},
    "hybride": {"co2_factor": 0.6, "consumption_factor": 0.65},
    "hybride_rechargeable": {"co2_factor": 0.4, "consumption_factor": 0.45},
    "electrique": {"co2_factor": 0.0, "consumption_factor": 0.0},
    "hydrogene": {"co2_factor": 0.0, "consumption_factor": 0.0},
}

TRANSMISSIONS = ["manuelle_5v", "manuelle_6v", "automatique_7v", "automatique_8v", "CVT", "double_embrayage_7v"]

COLORS = ["Noir Métallisé", "Blanc Nacré", "Gris Anthracite", "Bleu Marine", "Rouge Passion",
          "Argent", "Vert Émeraude", "Beige Sable", "Orange Volcanique", "Blanc Glacier"]

FEATURES_BY_CATEGORY = {
    "sécurité": ["ABS", "ESP", "Airbags frontaux", "Airbags latéraux", "Caméra de recul",
                 "Capteurs de stationnement", "Alerte franchissement de ligne",
                 "Freinage d'urgence automatique", "Régulateur de vitesse adaptatif",
                 "Détection angle mort", "Assistant maintien voie", "Vision nocturne"],
    "confort": ["Climatisation automatique", "Sièges chauffants", "Sièges ventilés",
                "Toit ouvrant", "Toit panoramique", "Direction assistée électrique",
                "Accoudoir central", "Réglage électrique sièges", "Mémoire position siège",
                "Démarrage sans clé", "Ouverture mains libres hayon"],
    "multimedia": ["Écran tactile 8\"", "Écran tactile 10\"", "Écran tactile 12\"",
                   "Apple CarPlay", "Android Auto", "Système de navigation GPS",
                   "Bluetooth", "Chargeur sans fil", "Enceintes premium", "DAB+ Radio",
                   "Affichage tête haute", "Tableau de bord numérique"],
    "aide_conduite": ["Pilote automatique", "Stationnement automatique",
                      "Assistance au remorquage", "Mode tout-terrain",
                      "Suspension pneumatique", "Différentiel actif",
                      "Contrôle de traction avancé"],
}

REVIEW_COMMENTS = [
    "Excellent rapport qualité-prix, très satisfait de mon achat.",
    "Consommation un peu élevée mais le confort est exceptionnel.",
    "Design magnifique et finitions de qualité supérieure.",
    "Très agréable à conduire, tenue de route impressionnante.",
    "Habitacle spacieux et bien équipé pour le prix.",
    "La technologie embarquée est vraiment innovante.",
    "Puissant et économique à la fois, parfait pour les longs trajets.",
    "Service après-vente excellent, équipe très professionnelle.",
    "Le silence de fonctionnement est remarquable.",
    "Idéal pour la ville comme pour les autoroutes.",
    "Quelques petits défauts mais dans l'ensemble très bon.",
    "Déception sur la qualité des matériaux intérieurs.",
    "Boîte de vitesses un peu hésitante mais moteur fantastique.",
    "Rapport prix/prestations imbattable dans sa catégorie.",
    "Mon meilleur achat depuis des années, je recommande vivement.",
    "Autonomie électrique décevante par temps froid.",
    "Interface multimédia intuitive et réactive.",
    "Visibilité arrière perfectible mais l'aide au stationnement compense.",
]

DEALERS = [
    {"name": "AutoElite Tunis", "city": "Tunis", "country": "Tunisia"},
    {"name": "Garage Central Paris", "city": "Paris", "country": "France"},
    {"name": "AutoPlus Lyon", "city": "Lyon", "country": "France"},
    {"name": "CarWorld Berlin", "city": "Berlin", "country": "Germany"},
    {"name": "Premium Motors Munich", "city": "Munich", "country": "Germany"},
    {"name": "AutoStar Milan", "city": "Milan", "country": "Italy"},
    {"name": "SpeedCars Madrid", "city": "Madrid", "country": "Spain"},
    {"name": "DriveZone Dubai", "city": "Dubai", "country": "UAE"},
    {"name": "MotorHub London", "city": "London", "country": "UK"},
    {"name": "EliteDrive Casablanca", "city": "Casablanca", "country": "Morocco"},
]


def get_price_range(brand_type, segment, fuel_type):
    base = {
        "mass_market": {"A": 12000, "B": 18000, "C": 25000, "D": 35000, "E": 45000,
                        "B-SUV": 22000, "C-SUV": 32000, "D-SUV": 48000, "MPV": 28000,
                        "Sport": 35000, "Pickup": 40000, "F": 60000},
        "premium":     {"B": 28000, "C": 38000, "D": 52000, "E": 70000, "F": 100000,
                        "B-SUV": 35000, "C-SUV": 55000, "D-SUV": 80000, "E-SUV": 110000,
                        "Sport": 90000, "A": 25000},
        "supercar":    {"GT": 220000, "Supercar": 300000, "Hypercar": 500000, "Luxury-SUV": 250000},
        "electrique":  {"C": 40000, "D": 60000, "E": 80000, "F": 110000,
                        "B": 30000, "C-SUV": 55000, "D-SUV": 75000, "E-SUV": 100000, "Pickup": 70000},
    }
    seg_map = base.get(brand_type, base["mass_market"])
    base_price = seg_map.get(segment, 25000)
    if fuel_type in ["hybride", "hybride_rechargeable"]:
        base_price *= 1.15
    elif fuel_type == "electrique":
        base_price *= 1.1
    variation = random.uniform(0.88, 1.12)
    return round(base_price * variation, -2)


def get_engine_specs(brand_type, fuel_type, segment):
    if fuel_type == "electrique":
        power = random.choice([136, 150, 170, 204, 218, 270, 306, 350, 408, 450, 560, 670])
        torque = power * random.uniform(2.0, 3.5)
        consumption = 0
        co2 = 0
        battery = random.choice([40, 52, 60, 75, 82, 100, 107, 118])
        range_km = int(battery * random.uniform(5.5, 7.5))
        engine_displacement = None
    elif fuel_type == "hydrogene":
        power = random.choice([163, 180])
        torque = 395
        consumption = 0
        co2 = 0
        battery = None
        range_km = random.randint(550, 700)
        engine_displacement = None
    else:
        if brand_type == "supercar":
            power = random.choice([570, 610, 640, 710, 765, 820, 1000])
            torque = power * random.uniform(0.9, 1.3)
            displacement = random.choice([3.9, 4.0, 5.2, 6.5])
        elif brand_type == "premium" and segment in ["E", "F", "Sport"]:
            power = random.choice([190, 204, 245, 286, 313, 340, 390, 450, 510])
            torque = power * random.uniform(1.1, 1.8)
            displacement = random.choice([2.0, 2.9, 3.0, 4.0])
        else:
            power = random.choice([65, 75, 90, 100, 110, 115, 130, 150, 160, 180, 200])
            torque = power * random.uniform(1.0, 1.7)
            displacement = random.choice([1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0])

        co2_factor = FUEL_TYPES[fuel_type]["co2_factor"]
        cons_factor = FUEL_TYPES[fuel_type]["consumption_factor"]
        base_consumption = power / 18
        consumption = round(base_consumption * cons_factor * random.uniform(0.9, 1.1), 1)
        co2 = round(consumption * 23.5 * co2_factor)
        battery = None
        range_km = None
        engine_displacement = displacement

    return {
        "puissance_ch": power,
        "couple_nm": round(torque),
        "consommation_l100km": consumption if fuel_type not in ["electrique", "hydrogene"] else None,
        "consommation_kwh100km": round(power / 10 * random.uniform(0.85, 1.1), 1) if fuel_type == "electrique" else None,
        "emissions_co2_gkm": co2 if fuel_type not in ["electrique", "hydrogene"] else 0,
        "batterie_kwh": battery,
        "autonomie_km": range_km,
        "cylindree_l": engine_displacement,
        "norme_emission": random.choice(["Euro 6d", "Euro 6d-TEMP", "Euro 6e"]) if fuel_type not in ["electrique", "hydrogene"] else "ZEV",
    }


def get_dimensions(body_type, segment):
    dims = {
        "hatchback": {"length": (3600, 4400), "width": (1650, 1820), "height": (1400, 1520), "trunk": (250, 380)},
        "sedan":     {"length": (4200, 5200), "width": (1750, 1900), "height": (1420, 1500), "trunk": (400, 580)},
        "suv":       {"length": (4100, 5000), "width": (1780, 1960), "height": (1550, 1750), "trunk": (400, 700)},
        "crossover": {"length": (3900, 4600), "width": (1720, 1850), "height": (1510, 1650), "trunk": (300, 520)},
        "coupe":     {"length": (4200, 4900), "width": (1800, 1990), "height": (1260, 1380), "trunk": (200, 350)},
        "cabriolet": {"length": (4200, 4700), "width": (1790, 1900), "height": (1260, 1380), "trunk": (180, 280)},
        "break":     {"length": (4500, 5000), "width": (1780, 1900), "height": (1450, 1560), "trunk": (500, 900)},
        "van":       {"length": (4300, 4900), "width": (1800, 1950), "height": (1700, 1900), "trunk": (600, 1000)},
        "pickup":    {"length": (5000, 5900), "width": (1850, 2050), "height": (1700, 1900), "trunk": (700, 1200)},
        "fastback":  {"length": (4700, 5100), "width": (1800, 1950), "height": (1380, 1460), "trunk": (380, 520)},
    }
    d = dims.get(body_type, dims["hatchback"])
    return {
        "longueur_mm": random.randint(*d["length"]),
        "largeur_mm": random.randint(*d["width"]),
        "hauteur_mm": random.randint(*d["height"]),
        "coffre_litres": random.randint(*d["trunk"]),
        "nombre_places": 7 if body_type in ["van", "suv"] and random.random() > 0.5 else 5,
        "nombre_portes": 3 if body_type in ["hatchback", "coupe"] and random.random() > 0.6 else (2 if body_type == "cabriolet" else (4 if body_type != "van" else 5)),
    }


def generate_reviews(brand, model_name, n=None):
    n = n or random.randint(2, 6)
    reviews = []
    base_date = datetime(2022, 1, 1)
    for _ in range(n):
        days_offset = random.randint(0, 900)
        date = base_date + timedelta(days=days_offset)
        rating = round(random.gauss(4.0, 0.7), 1)
        rating = max(1.0, min(5.0, rating))
        reviews.append({
            "auteur": f"Client_{random.randint(1000, 9999)}",
            "note": round(rating * 2) / 2,
            "commentaire": random.choice(REVIEW_COMMENTS),
            "date": date.strftime("%Y-%m-%d"),
            "verified_purchase": random.choice([True, True, True, False]),
            "aspects": {
                "confort": round(random.uniform(3.0, 5.0), 1),
                "performance": round(random.uniform(3.0, 5.0), 1),
                "economie": round(random.uniform(2.5, 5.0), 1),
                "fiabilite": round(random.uniform(3.0, 5.0), 1),
                "valeur": round(random.uniform(3.0, 5.0), 1),
            }
        })
    return reviews


def generate_features(brand_type, segment):
    selected = []
    for cat, feats in FEATURES_BY_CATEGORY.items():
        if brand_type == "supercar":
            n = random.randint(3, min(6, len(feats)))
        elif brand_type == "premium":
            n = random.randint(3, min(5, len(feats)))
        else:
            n = random.randint(2, min(4, len(feats)))
        selected.extend(random.sample(feats, n))
    return selected


def generate_stock():
    return {
        "disponible": random.choice([True, True, True, False]),
        "quantite_stock": random.randint(0, 25),
        "delai_livraison_semaines": random.randint(1, 20),
        "concessionnaires": random.sample(DEALERS, random.randint(1, 4)),
        "commande_possible": True,
    }


# ── Main generation ───────────────────────────────────────────────────────────
documents = []
doc_id = 1

for brand_name, brand_info in BRANDS.items():
    for model_info in brand_info["models"]:
        # Determine valid fuel types for this model
        if model_info["type"] == "electrique":
            valid_fuels = ["electrique"]
        elif model_info["type"] == "hydrogene":
            valid_fuels = ["hydrogene"]
        elif model_info["type"] == "sport" and brand_info["type"] == "supercar":
            valid_fuels = ["essence"]
        elif model_info["type"] == "hybride":
            valid_fuels = ["hybride_rechargeable"]
        elif brand_info["type"] == "mass_market":
            valid_fuels = ["essence", "diesel", "hybride", "essence"]
        elif brand_info["type"] == "premium":
            valid_fuels = ["essence", "diesel", "hybride", "hybride_rechargeable"]
        else:
            valid_fuels = ["essence"]

        years = [2020, 2021, 2022, 2023, 2024]
        for year in random.sample(years, random.randint(2, 4)):
            fuel = random.choice(valid_fuels)
            if model_info["type"] == "electrique":
                fuel = "electrique"

            engine = get_engine_specs(brand_info["type"], fuel, model_info["segment"])
            price = get_price_range(brand_info["type"], model_info["segment"], fuel)
            dims = get_dimensions(model_info["body"], model_info["segment"])
            reviews = generate_reviews(brand_name, model_info["name"])
            avg_rating = round(sum(r["note"] for r in reviews) / len(reviews), 1)

            # Transmission
            if fuel == "electrique" or fuel == "hydrogene":
                transmission = "automatique_1v"
            elif model_info["type"] == "sport" and brand_info["type"] == "supercar":
                transmission = random.choice(["automatique_7v", "double_embrayage_7v"])
            else:
                transmission = random.choice(TRANSMISSIONS)

            doc = {
                "_id": f"car_{doc_id:04d}",
                "marque": brand_name,
                "modele": model_info["name"],
                "annee": year,
                "type_vehicule": model_info["type"],
                "carrosserie": model_info["body"],
                "segment": model_info["segment"],

                "constructeur": {
                    "nom": brand_name,
                    "pays": brand_info["country"],
                    "annee_fondation": brand_info["founded"],
                    "categorie": brand_info["type"],
                },

                "motorisation": {
                    "type_carburant": fuel,
                    "transmission": transmission,
                    **engine,
                },

                "prix": {
                    "prix_base_eur": price,
                    "prix_options_eur": round(price * random.uniform(0.05, 0.25), -2),
                    "prix_total_ttc_eur": round(price * random.uniform(1.05, 1.30), -2),
                    "loyer_mensuel_eur": round(price / random.randint(36, 60), -1),
                },

                "dimensions": dims,

                "couleurs_disponibles": random.sample(COLORS, random.randint(4, 8)),
                "couleur_exemple": random.choice(COLORS),

                "equipements": generate_features(brand_info["type"], model_info["segment"]),

                "garantie": {
                    "duree_ans": 3 if brand_info["type"] != "supercar" else 2,
                    "kilometrage_max": 100000,
                    "batterie_ans": 8 if fuel in ["electrique", "hybride_rechargeable"] else None,
                },

                "avis": reviews,
                "note_moyenne": avg_rating,
                "nombre_avis": len(reviews),

                "stock": generate_stock(),

                "tags": [
                    brand_name.lower(),
                    model_info["name"].lower().replace(" ", "_"),
                    model_info["type"],
                    model_info["body"],
                    fuel,
                    str(year),
                    model_info["segment"].lower(),
                    brand_info["country"].lower(),
                    brand_info["type"],
                ],

                "description": (
                    f"La {brand_name} {model_info['name']} {year} est une {model_info['type']} "
                    f"de segment {model_info['segment']} propulsée par un moteur {fuel} "
                    f"de {engine['puissance_ch']} ch. "
                    f"Avec une note moyenne de {avg_rating}/5, elle représente un excellent choix "
                    f"dans la catégorie {model_info['body']}."
                ),

                "date_ajout": datetime(2024, random.randint(1, 12), random.randint(1, 28)).strftime("%Y-%m-%d"),
            }

            documents.append(doc)
            doc_id += 1

# Save

output_path = "C:/Users/HP/Documents/Desktop/TEK-UP/SEM 2/AI/rag_studio/cars_dataset_mongodb.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(documents, f, ensure_ascii=False, indent=2)

print(f"✅ Generated {len(documents)} car documents")
print(f"📁 Saved to: {output_path}")

# Stats
from collections import Counter
brands_count = Counter(d["marque"] for d in documents)
types_count = Counter(d["type_vehicule"] for d in documents)
fuels_count = Counter(d["motorisation"]["type_carburant"] for d in documents)

print(f"\n📊 Stats:")
print(f"  Brands: {dict(brands_count)}")
print(f"  Types: {dict(types_count)}")
print(f"  Fuels: {dict(fuels_count)}")
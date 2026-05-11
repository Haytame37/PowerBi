import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

np.random.seed(42)
random.seed(42)

os.makedirs('data_oee', exist_ok=True)

# ── 1. TABLE MACHINES ───────────────────────────────────────────────
machines = pd.DataFrame({
    'machine_id': ['M01', 'M02', 'M03', 'M04', 'M05'],
    'nom_machine': ['Fraiseuse CNC Alpha', 'Tour CNC Beta', 'Presse Hydraulique Gamma',
                    'Robot Soudure Delta', 'Ligne Assemblage Epsilon'],
    'ligne':       ['Ligne A', 'Ligne A', 'Ligne B', 'Ligne B', 'Ligne C'],
    'capacite_theorique_heure': [120, 100, 200, 80, 150],
    'temps_cycle_standard_sec': [30, 36, 18, 45, 24],
    'date_installation': ['2019-03-15', '2020-07-22', '2018-11-01', '2021-02-10', '2022-05-18'],
    'responsable': ['Ahmed K.', 'Sara M.', 'Karim B.', 'Nadia L.', 'Youssef T.']
})
machines.to_csv('data_oee/machines.csv', index=False)

# ── 2. TABLE SHIFTS ─────────────────────────────────────────────────
shifts = pd.DataFrame({
    'shift_id': ['S1', 'S2', 'S3'],
    'nom_shift': ['Matin', 'Après-midi', 'Nuit'],
    'heure_debut': ['06:00', '14:00', '22:00'],
    'heure_fin':   ['14:00', '22:00', '06:00'],
    'duree_heures': [8, 8, 8],
    'operateurs': ['Équipe A', 'Équipe B', 'Équipe C']
})
shifts.to_csv('data_oee/shifts.csv', index=False)

# ── 3. TABLE CAUSES ARRÊTS ──────────────────────────────────────────
causes_arrets = pd.DataFrame({
    'cause_id': ['CA01','CA02','CA03','CA04','CA05','CA06','CA07','CA08'],
    'categorie': ['Panne','Panne','Maintenance','Maintenance','Qualité','Qualité','Organisationnel','Organisationnel'],
    'description': ['Panne mécanique','Panne électrique','Maintenance préventive','Changement d\'outil',
                    'Réglage qualité','Contrôle produit','Manque matière','Changement de série'],
    'criticite': ['Haute','Haute','Moyenne','Moyenne','Faible','Faible','Moyenne','Faible']
})
causes_arrets.to_csv('data_oee/causes_arrets.csv', index=False)

# ── 4. TABLE PRODUCTION (365 jours × 5 machines × 3 shifts) ─────────
start = datetime(2024, 1, 1)
records = []

oee_profiles = {
    'M01': {'d_base':0.88, 'p_base':0.91, 'q_base':0.96, 'volatilite':0.05},
    'M02': {'d_base':0.82, 'p_base':0.87, 'q_base':0.94, 'volatilite':0.07},
    'M03': {'d_base':0.75, 'p_base':0.83, 'q_base':0.91, 'volatilite':0.09},
    'M04': {'d_base':0.92, 'p_base':0.95, 'q_base':0.98, 'volatilite':0.03},
    'M05': {'d_base':0.79, 'p_base':0.89, 'q_base':0.93, 'volatilite':0.06},
}

for day_offset in range(365):
    date = start + timedelta(days=day_offset)
    jour_semaine = date.weekday()
    if jour_semaine >= 6: continue  # Pas de dimanche

    for mid, mrow in machines.iterrows():
        machine_id = mrow['machine_id']
        cap = mrow['capacite_theorique_heure']
        prof = oee_profiles[machine_id]

        for sid, srow in shifts.iterrows():
            if jour_semaine == 5 and srow['shift_id'] == 'S3': continue  # Pas nuit samedi

            vol = prof['volatilite']
            # Tendance saisonnière + bruit
            saison = 0.03 * np.sin(2 * np.pi * day_offset / 365)
            d = min(max(prof['d_base'] + saison + np.random.normal(0, vol), 0.50), 0.99)
            p = min(max(prof['p_base'] + saison + np.random.normal(0, vol*0.8), 0.55), 0.99)
            q = min(max(prof['q_base'] + np.random.normal(0, vol*0.4), 0.80), 0.999)

            # Pannes rares ponctuelles
            if random.random() < 0.03:
                d *= random.uniform(0.5, 0.75)

            oee = d * p * q
            temps_requis = srow['duree_heures'] * 60  # minutes
            temps_marche = d * temps_requis
            prod_theorique = cap * srow['duree_heures']
            prod_reelle = int(p * prod_theorique)
            prod_conforme = int(q * prod_reelle)
            rebuts = prod_reelle - prod_conforme
            temps_arret = temps_requis - temps_marche

            records.append({
                'date': date.strftime('%Y-%m-%d'),
                'machine_id': machine_id,
                'shift_id': srow['shift_id'],
                'disponibilite': round(d, 4),
                'performance': round(p, 4),
                'qualite': round(q, 4),
                'oee': round(oee, 4),
                'temps_requis_min': round(temps_requis, 1),
                'temps_marche_min': round(temps_marche, 1),
                'temps_arret_min': round(temps_arret, 1),
                'production_theorique': prod_theorique,
                'production_reelle': prod_reelle,
                'production_conforme': prod_conforme,
                'rebuts': rebuts,
                'mois': date.strftime('%Y-%m'),
                'semaine': date.strftime('%Y-W%V'),
                'jour_semaine': date.strftime('%A')
            })

production = pd.DataFrame(records)
production.to_csv('data_oee/production.csv', index=False)

# ── 5. TABLE ARRÊTS DÉTAILLÉS ────────────────────────────────────────
arret_records = []
causes_list = causes_arrets['cause_id'].tolist()
causes_weights = [0.20, 0.15, 0.18, 0.12, 0.10, 0.08, 0.10, 0.07]

for _, row in production.iterrows():
    if row['temps_arret_min'] > 5:
        n_arrets = random.randint(1, 4)
        durees = np.random.dirichlet(np.ones(n_arrets)) * row['temps_arret_min']
        for i, dur in enumerate(durees):
            if dur < 2: continue
            cause = random.choices(causes_list, weights=causes_weights)[0]
            arret_records.append({
                'arret_id': f"AR{len(arret_records)+1:05d}",
                'date': row['date'],
                'machine_id': row['machine_id'],
                'shift_id': row['shift_id'],
                'cause_id': cause,
                'duree_minutes': round(dur, 1),
                'mois': row['mois']
            })

arrets = pd.DataFrame(arret_records)
arrets.to_csv('data_oee/arrets.csv', index=False)

# ── STATS SUMMARY ────────────────────────────────────────────────────
print("✅ DONNÉES GÉNÉRÉES AVEC SUCCÈS\n")
print(f"📊 Production : {len(production):,} enregistrements")
print(f"🔴 Arrêts     : {len(arrets):,} événements")
print(f"\n📈 OEE Moyen Global : {production['oee'].mean():.1%}")
print("\n🏭 OEE par Machine :")
print(production.groupby('machine_id')['oee'].mean().apply(lambda x: f"{x:.1%}"))
print(f"\n📁 Fichiers sauvegardés dans data_oee/")

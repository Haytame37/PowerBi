# 🏭 Industrial OEE Analytics Dashboard — Big Data & Real-Time

Ce projet est une solution complète de monitoring industriel axée sur l'**OEE (Overall Equipment Effectiveness)** ou **TRS (Taux de Rendement Synthétique)**. Il combine une analyse historique (Big Data) avec un suivi en temps réel via WebSockets.

---

## 📋 Table des Matières
1. [Aperçu du Projet](#aperçu-du-projet)
2. [Architecture Technique](#architecture-technique)
3. [Structure du Projet](#structure-du-projet)
4. [Installation et Configuration](#installation-et-configuration)
5. [Utilisation](#utilisation)
   - [Mode Statique (Historique)](#mode-statique-historique)
   - [Mode Temps Réel (API & WebSocket)](#mode-temps-réel-api--websocket)
6. [KPIs et Mesures DAX](#kpis-et-mesures-dax)
7. [Collaboration (Groupe)](#collaboration-groupe)

---

## 🌟 Aperçu du Projet

L'objectif est de fournir aux responsables de production une vue à 360° sur la performance des machines :
- **Disponibilité** : Suivi des pannes et arrêts.
- **Performance** : Comparaison entre la vitesse réelle et la capacité théorique.
- **Qualité** : Analyse des taux de rebuts.
- **OEE Global** : Score de performance synthétique.

---

## 🛠 Architecture Technique

- **Backend** : Python 3 + Flask (API REST) + Flask-SocketIO (WebSocket).
- **Frontend** : HTML5 / CSS3 / JavaScript (Chart.js pour les graphiques).
- **Data Science** : Pandas & NumPy pour la génération et le traitement des données.
- **PowerBI Integration** : Modèle de données optimisé et mesures DAX fournies.

---

## 📂 Structure du Projet

```text
projet_oee_complet/
├── 📊 dashboard_oee.html         # Dashboard principal (analyse historique)
├── ⚡ dashboard_temps_reel.html  # Dashboard WebSocket (monitoring live)
├── 🐍 api_oee.py                 # Serveur Flask + Logique WebSocket
├── ⚙️ generate_data.py           # Script de génération de datasets CSV
├── 📂 data_oee/                  # Datasets générés (CSVs)
│   ├── production.csv            # Données de prod journalières
│   ├── arrets.csv                # Détails des causes d'arrêts
│   ├── machines.csv              # Registre des équipements
│   ├── shifts.csv                # Configuration des équipes (3x8)
│   └── causes_arrets.csv         # Référentiel des pannes
└── 📄 docs/
    └── mesures_DAX_complet.md    # Bibliothèque de formules pour PowerBI
```

---

## 🚀 Installation et Configuration

### 1. Prérequis
- Python 3.8+ installé.
- Navigateur moderne (Chrome/Edge/Firefox).

### 2. Installation des dépendances
Ouvrez votre terminal dans le dossier du projet et exécutez :
```bash
pip install flask flask-socketio flask-cors eventlet pandas numpy
```

### 3. Génération des données
Si vous souhaitez régénérer les fichiers CSV (par défaut 1 an de données) :
```bash
python generate_data.py
```

---

## 📈 Utilisation

### Mode Statique (Historique)
Idéal pour analyser les tendances passées.
- Ouvrez simplement `dashboard_oee.html` dans votre navigateur.
- Ce dashboard utilise les données consolidées pour afficher l'OEE global par machine et par ligne.

### Mode Temps Réel (API & WebSocket)
Simule un environnement d'usine connectée (SCADA/IoT).
1. Lancez l'API :
   ```bash
   python api_oee.py
   ```
2. Ouvrez `dashboard_temps_reel.html`.
3. Vous verrez les machines changer d'état (Running, Warning, Stopped) en direct, avec des alertes WebSocket lors des pannes.

---

## 📊 KPIs et Mesures DAX

Pour l'intégration dans **Power BI**, consultez le fichier `docs/mesures_DAX_complet.md`. Il contient les formules prêtes à l'emploi pour :
- **OEE %** = `DIVIDE([Prod Conforme], [Capacité Théorique])`
- **Taux de Disponibilité** = `[Temps de Marche] / [Temps Requis]`
- **Taux de Performance** = `[Prod Réelle] / ([Capacité Horaire] * [Temps de Marche])`
- **Taux de Qualité** = `[Prod Conforme] / [Prod Réelle]`

---

## 🤝 Collaboration (Groupe)

Pour travailler efficacement en équipe :
1. **Branchement** : Créez une branche par fonctionnalité (`git checkout -b feature-nom`).
2. **Modifications** : Documentez vos changements dans le code.
3. **PowerBI** : Si vous créez un fichier `.pbix`, placez-le dans un nouveau dossier `powerbi_reports/`.
4. **Data** : Ne modifiez pas manuellement les CSV dans `data_oee/`, utilisez plutôt `generate_data.py` pour garder la cohérence.

---
*Projet réalisé dans le cadre du module Big Data - ENSA Beni Mellal.*

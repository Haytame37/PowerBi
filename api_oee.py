"""
╔══════════════════════════════════════════════════════════════╗
║         API TEMPS RÉEL — OEE / TRS Ligne de Production      ║
║         Flask REST + WebSocket (Socket.IO)                   ║
║         Simule un flux SCADA/MES industriel                  ║
╚══════════════════════════════════════════════════════════════╝

ENDPOINTS REST :
  GET /api/status          → Statut de l'API
  GET /api/machines        → Liste des machines
  GET /api/oee/current     → OEE instantané toutes les machines
  GET /api/oee/history     → Historique des 60 dernières mesures
  GET /api/oee/machine/<id>→ OEE d'une machine spécifique
  GET /api/arrets/live     → Derniers arrêts détectés
  GET /api/kpis            → KPIs agrégés globaux

WEBSOCKET (Socket.IO) :
  Event 'oee_update'       → Émis toutes les 2 secondes
  Event 'arret_detecte'    → Émis lors d'une panne
  Event 'alerte'           → Émis si OEE < seuil critique
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
import random
import numpy as np
from datetime import datetime, timedelta
from collections import deque

# ── APP SETUP ──────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'oee_secret_2024'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ── CONFIGURATION MACHINES ─────────────────────────────────────────
MACHINES = {
    'M01': {
        'nom': 'Fraiseuse CNC Alpha', 'ligne': 'A',
        'oee_base': 0.757, 'dispo_base': 0.870, 'perf_base': 0.907, 'qual_base': 0.959,
        'capacite_h': 120, 'volatilite': 0.025, 'statut': 'running',
        'responsable': 'Ahmed K.'
    },
    'M02': {
        'nom': 'Tour CNC Beta', 'ligne': 'A',
        'oee_base': 0.668, 'dispo_base': 0.814, 'perf_base': 0.871, 'qual_base': 0.941,
        'capacite_h': 100, 'volatilite': 0.030, 'statut': 'running',
        'responsable': 'Sara M.'
    },
    'M03': {
        'nom': 'Presse Hydraulique Gamma', 'ligne': 'B',
        'oee_base': 0.561, 'dispo_base': 0.742, 'perf_base': 0.830, 'qual_base': 0.911,
        'capacite_h': 200, 'volatilite': 0.040, 'statut': 'warning',
        'responsable': 'Karim B.'
    },
    'M04': {
        'nom': 'Robot Soudure Delta', 'ligne': 'B',
        'oee_base': 0.843, 'dispo_base': 0.907, 'perf_base': 0.948, 'qual_base': 0.980,
        'capacite_h': 80, 'volatilite': 0.015, 'statut': 'running',
        'responsable': 'Nadia L.'
    },
    'M05': {
        'nom': 'Ligne Assemblage Epsilon', 'ligne': 'C',
        'oee_base': 0.647, 'dispo_base': 0.782, 'perf_base': 0.890, 'qual_base': 0.930,
        'capacite_h': 150, 'volatilite': 0.028, 'statut': 'running',
        'responsable': 'Youssef T.'
    }
}

CAUSES_ARRET = [
    {'id': 'CA01', 'desc': 'Panne mécanique',    'cat': 'Panne',           'poids': 20},
    {'id': 'CA02', 'desc': 'Panne électrique',   'cat': 'Panne',           'poids': 15},
    {'id': 'CA03', 'desc': 'Maintenance préventive', 'cat': 'Maintenance', 'poids': 18},
    {'id': 'CA04', 'desc': "Changement d'outil", 'cat': 'Maintenance',     'poids': 12},
    {'id': 'CA05', 'desc': 'Réglage qualité',    'cat': 'Qualité',         'poids': 10},
    {'id': 'CA06', 'desc': 'Manque matière',     'cat': 'Organisationnel', 'poids': 10},
    {'id': 'CA07', 'desc': 'Contrôle produit',   'cat': 'Qualité',         'poids': 8},
    {'id': 'CA08', 'desc': 'Changement de série','cat': 'Organisationnel', 'poids': 7},
]

# ── ÉTAT GLOBAL EN MÉMOIRE ─────────────────────────────────────────
historique      = deque(maxlen=60)   # 60 dernières mesures (2 min)
arrets_live     = deque(maxlen=20)   # 20 derniers arrêts
alertes_active  = {}
tick            = 0
machine_states  = {mid: {'dispo': m['dispo_base'], 'perf': m['perf_base'],
                          'qual': m['qual_base'], 'en_arret': False,
                          'arret_restant': 0, 'prod_session': 0}
                   for mid, m in MACHINES.items()}


def generer_mesure():
    """Génère une nouvelle mesure OEE pour toutes les machines."""
    global tick
    tick += 1
    ts = datetime.now().isoformat()
    mesures = {}

    for mid, machine in MACHINES.items():
        state = machine_states[mid]
        vol   = machine['volatilite']

        # ── Simulation panne aléatoire ──────────────────────────
        if not state['en_arret'] and random.random() < 0.018:
            state['en_arret']      = True
            state['arret_restant'] = random.randint(3, 12)  # ticks
            cause = random.choices(CAUSES_ARRET,
                                   weights=[c['poids'] for c in CAUSES_ARRET])[0]
            arret_evt = {
                'id':        f"AR{tick:05d}",
                'timestamp': ts,
                'machine_id': mid,
                'machine':   machine['nom'],
                'cause':     cause['desc'],
                'categorie': cause['cat'],
                'duree_estimee_min': state['arret_restant'] * 2,
                'severite':  'haute' if cause['cat'] == 'Panne' else 'moyenne'
            }
            arrets_live.appendleft(arret_evt)
            socketio.emit('arret_detecte', arret_evt)

        # ── Résolution panne ────────────────────────────────────
        if state['en_arret']:
            state['arret_restant'] -= 1
            if state['arret_restant'] <= 0:
                state['en_arret'] = False

        # ── Calcul valeurs avec bruit + tendance ────────────────
        if state['en_arret']:
            d = max(machine['dispo_base'] * random.uniform(0.45, 0.65), 0.30)
        else:
            bruit = np.random.normal(0, vol)
            d = float(np.clip(machine['dispo_base'] + bruit, 0.50, 0.99))

        p = float(np.clip(machine['perf_base'] + np.random.normal(0, vol * 0.6), 0.55, 0.99))
        q = float(np.clip(machine['qual_base'] + np.random.normal(0, vol * 0.3), 0.80, 0.999))
        oee = d * p * q

        # ── Production instantanée (pièces/2sec) ────────────────
        prod_rate = machine['capacite_h'] / 1800  # pièces par 2 secondes
        prod_inst = int(p * prod_rate * (1 if not state['en_arret'] else 0))
        rebuts    = int(prod_inst * (1 - q))
        state['prod_session'] += prod_inst

        # ── Mise à jour état ────────────────────────────────────
        state['dispo'] = d
        state['perf']  = p
        state['qual']  = q

        statut = 'stopped' if state['en_arret'] else (
                 'critical' if oee < 0.65 else
                 'warning'  if oee < 0.75 else 'running')

        mesures[mid] = {
            'machine_id':    mid,
            'nom':           machine['nom'],
            'ligne':         f"Ligne {machine['ligne']}",
            'disponibilite': round(d, 4),
            'performance':   round(p, 4),
            'qualite':       round(q, 4),
            'oee':           round(oee, 4),
            'statut':        statut,
            'en_arret':      state['en_arret'],
            'prod_instant':  prod_inst,
            'rebuts_instant': rebuts,
            'prod_session':  state['prod_session'],
            'responsable':   machine['responsable'],
        }

        # ── Alerte OEE critique ─────────────────────────────────
        if oee < 0.60 and mid not in alertes_active:
            alertes_active[mid] = True
            socketio.emit('alerte', {
                'type':    'oee_critique',
                'machine': machine['nom'],
                'machine_id': mid,
                'oee':     round(oee, 4),
                'message': f"⚠ OEE critique sur {machine['nom']} : {oee:.1%}",
                'timestamp': ts
            })
        elif oee >= 0.65 and mid in alertes_active:
            del alertes_active[mid]

    # ── OEE Global ──────────────────────────────────────────────
    oee_global   = float(np.mean([m['oee']           for m in mesures.values()]))
    dispo_global = float(np.mean([m['disponibilite'] for m in mesures.values()]))
    perf_global  = float(np.mean([m['performance']   for m in mesures.values()]))
    qual_global  = float(np.mean([m['qualite']       for m in mesures.values()]))
    prod_total   = sum(m['prod_instant'] for m in mesures.values())

    payload = {
        'tick':       tick,
        'timestamp':  ts,
        'global': {
            'oee':           round(oee_global, 4),
            'disponibilite': round(dispo_global, 4),
            'performance':   round(perf_global, 4),
            'qualite':       round(qual_global, 4),
            'prod_instant':  prod_total,
            'machines_en_arret': sum(1 for m in mesures.values() if m['en_arret'])
        },
        'machines': mesures
    }
    historique.appendleft(payload)
    return payload


# ── BOUCLE TEMPS RÉEL ──────────────────────────────────────────────
def boucle_emission():
    """Émet les données via WebSocket toutes les 2 secondes."""
    print("🚀 Boucle temps réel démarrée — émission toutes les 2s")
    while True:
        payload = generer_mesure()
        socketio.emit('oee_update', payload)
        eventlet.sleep(2)


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS REST
# ═══════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return jsonify({
        'api': 'OEE Analytics API',
        'version': '1.0.0',
        'description': 'API temps réel pour le suivi OEE/TRS de ligne de production',
        'endpoints': {
            'GET /api/status':            'Statut de l\'API',
            'GET /api/machines':          'Liste des machines',
            'GET /api/oee/current':       'OEE instantané',
            'GET /api/oee/history':       'Historique 60 mesures',
            'GET /api/oee/machine/<id>':  'OEE machine spécifique',
            'GET /api/arrets/live':       'Derniers arrêts',
            'GET /api/kpis':              'KPIs agrégés',
        },
        'websocket': {
            'url':    'ws://localhost:5000',
            'events': ['oee_update', 'arret_detecte', 'alerte']
        }
    })


@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'operational',
        'tick': tick,
        'uptime_s': tick * 2,
        'machines_actives': len(MACHINES),
        'machines_en_arret': sum(1 for s in machine_states.values() if s['en_arret']),
        'alertes_actives': len(alertes_active),
        'historique_size': len(historique),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/machines')
def api_machines():
    return jsonify({
        'count': len(MACHINES),
        'machines': [
            {
                'id': mid,
                'nom': m['nom'],
                'ligne': f"Ligne {m['ligne']}",
                'capacite_h': m['capacite_h'],
                'responsable': m['responsable'],
                'statut_actuel': machine_states[mid]['en_arret'] and 'arrêt' or 'marche'
            }
            for mid, m in MACHINES.items()
        ]
    })


@app.route('/api/oee/current')
def api_oee_current():
    if not historique:
        return jsonify({'error': 'Pas encore de données'}), 503
    return jsonify(historique[0])


@app.route('/api/oee/history')
def api_oee_history():
    return jsonify({
        'count': len(historique),
        'history': list(historique)
    })


@app.route('/api/oee/machine/<machine_id>')
def api_oee_machine(machine_id):
    if machine_id not in MACHINES:
        return jsonify({'error': f'Machine {machine_id} inconnue'}), 404
    if not historique:
        return jsonify({'error': 'Pas encore de données'}), 503

    derniere = historique[0]
    machine_data = derniere['machines'].get(machine_id, {})

    series_oee   = [h['machines'][machine_id]['oee']           for h in historique if machine_id in h['machines']]
    series_dispo = [h['machines'][machine_id]['disponibilite'] for h in historique if machine_id in h['machines']]

    return jsonify({
        'machine_id':  machine_id,
        'info':        MACHINES[machine_id],
        'current':     machine_data,
        'oee_moyen':   round(float(np.mean(series_oee)), 4) if series_oee else None,
        'dispo_moyen': round(float(np.mean(series_dispo)), 4) if series_dispo else None,
        'serie_oee':   [round(v, 4) for v in series_oee],
        'timestamp':   derniere['timestamp']
    })


@app.route('/api/arrets/live')
def api_arrets_live():
    return jsonify({
        'count': len(arrets_live),
        'arrets': list(arrets_live)
    })


@app.route('/api/kpis')
def api_kpis():
    if len(historique) < 2:
        return jsonify({'error': 'Données insuffisantes'}), 503

    all_oee   = [h['global']['oee']           for h in historique]
    all_dispo = [h['global']['disponibilite'] for h in historique]
    all_perf  = [h['global']['performance']   for h in historique]
    all_qual  = [h['global']['qualite']       for h in historique]

    prod_session = sum(
        sum(m['prod_session'] for m in h['machines'].values())
        for h in [historique[0]]
    )

    return jsonify({
        'periode_mesure_s': len(historique) * 2,
        'oee_moyen':        round(float(np.mean(all_oee)), 4),
        'oee_min':          round(float(np.min(all_oee)), 4),
        'oee_max':          round(float(np.max(all_oee)), 4),
        'dispo_moy':        round(float(np.mean(all_dispo)), 4),
        'perf_moy':         round(float(np.mean(all_perf)), 4),
        'qual_moy':         round(float(np.mean(all_qual)), 4),
        'nb_arrets_session': len(arrets_live),
        'alertes_actives':  list(alertes_active.keys()),
        'production_session': prod_session,
        'machines_probleme': [
            mid for mid, s in machine_states.items() if s['en_arret']
        ]
    })


# ── WEBSOCKET EVENTS ───────────────────────────────────────────────
@socketio.on('connect')
def on_connect():
    print(f"✅ Client connecté : {datetime.now().strftime('%H:%M:%S')}")
    if historique:
        emit('oee_update', historique[0])
    emit('connected', {
        'message': 'Connexion WebSocket OEE établie',
        'machines': list(MACHINES.keys()),
        'interval_ms': 2000
    })

@socketio.on('disconnect')
def on_disconnect():
    print(f"❌ Client déconnecté : {datetime.now().strftime('%H:%M:%S')}")

@socketio.on('ping_client')
def on_ping(data):
    emit('pong_server', {'ts': datetime.now().isoformat()})


# ── LANCEMENT ──────────────────────────────────────────────────────
if __name__ == '__main__':
    print("╔══════════════════════════════════════════════╗")
    print("║   🏭  OEE Real-Time API  —  v1.0.0          ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  REST API  →  http://localhost:5000          ║")
    print("║  WebSocket →  ws://localhost:5000            ║")
    print("║  Dashboard →  ouvrir dashboard_rt.html      ║")
    print("╚══════════════════════════════════════════════╝")

    # Démarrer la boucle temps réel dans un thread séparé
    thread = threading.Thread(target=boucle_emission, daemon=True)
    thread.start()

    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

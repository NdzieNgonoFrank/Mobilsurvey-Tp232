import os
import json
import random
from datetime import datetime, timedelta

import pandas as pd
import plotly
import plotly.express as px
from flask import Flask, render_template, request, redirect, url_for, session

from models import db, Reponse

# ─── Configuration ────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'inf232-mobisurvey-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///habitudes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# ─── Données de démonstration ─────────────────────────────────────────────────
def seed_demo_data():
    """Insère 30 réponses fictives si la base est vide."""
    if Reponse.query.count() > 0:
        return

    niveaux    = ['L1', 'L2', 'L3', 'Master 1', 'Master 2']
    appareils  = ['Entrée de gamme', 'Milieu de gamme', 'Haut de gamme']
    operateurs = ['MTN', 'Orange', 'Camtel', 'Autre']
    forfaits   = ['Journalier', 'Hebdomadaire', 'Mensuel']
    apps_dispo = ['WhatsApp', 'TikTok', 'YouTube', 'Facebook',
                  'Instagram', 'Telegram', 'Twitter']

    random.seed(42)
    for _ in range(30):
        apps = random.sample(apps_dispo, random.randint(2, 5))
        r = Reponse(
            niveau_etudes       = random.choice(niveaux),
            appareil            = random.choices(appareils, weights=[0.40, 0.45, 0.15])[0],
            operateur           = random.choices(operateurs, weights=[0.50, 0.40, 0.05, 0.05])[0],
            type_forfait        = random.choices(forfaits, weights=[0.30, 0.35, 0.35])[0],
            depenses_mensuelles = round(random.uniform(1000, 15000) / 100) * 100,
            heures_telephone    = round(random.uniform(1.0, 12.0), 1),
            heures_streaming    = round(random.uniform(0.0, 5.0), 1),
            apps_utilisees      = ','.join(apps),
            date_reponse        = datetime.utcnow() - timedelta(days=random.randint(0, 30)),
        )
        db.session.add(r)
    db.session.commit()


# Initialisation DB + seed au démarrage
with app.app_context():
    db.create_all()
    seed_demo_data()


# ─── Helpers ──────────────────────────────────────────────────────────────────
LAYOUT_BASE = dict(
    template      = 'plotly_dark',
    paper_bgcolor = 'rgba(0,0,0,0)',
    plot_bgcolor  = 'rgba(22,27,34,0.6)',
    font          = dict(family='Poppins, sans-serif', color='#C9D1D9'),
    margin        = dict(l=20, r=20, t=50, b=30),
)


def to_json(fig):
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    total = Reponse.query.count()
    return render_template('index.html', total=total)


# --- Formulaire multi-étapes ---

@app.route('/formulaire/etape1', methods=['GET', 'POST'])
def etape1():
    erreur = None
    if request.method == 'POST':
        niveau   = request.form.get('niveau_etudes', '').strip()
        appareil = request.form.get('appareil', '').strip()
        if not niveau or not appareil:
            erreur = "Veuillez remplir tous les champs."
        else:
            session['etape1'] = {'niveau_etudes': niveau, 'appareil': appareil}
            return redirect(url_for('etape2'))
    return render_template('etape1.html', erreur=erreur)


@app.route('/formulaire/etape2', methods=['GET', 'POST'])
def etape2():
    if 'etape1' not in session:
        return redirect(url_for('etape1'))
    erreur = None
    if request.method == 'POST':
        operateur = request.form.get('operateur', '').strip()
        forfait   = request.form.get('type_forfait', '').strip()
        dep_str   = request.form.get('depenses_mensuelles', '').strip()
        if not operateur or not forfait or not dep_str:
            erreur = "Veuillez remplir tous les champs."
        else:
            try:
                depenses = float(dep_str)
                if depenses < 0:
                    raise ValueError
            except ValueError:
                erreur = "Montant de dépenses invalide."
            else:
                session['etape2'] = {
                    'operateur': operateur,
                    'type_forfait': forfait,
                    'depenses_mensuelles': depenses,
                }
                return redirect(url_for('etape3'))
    return render_template('etape2.html', erreur=erreur)


@app.route('/formulaire/etape3', methods=['GET', 'POST'])
def etape3():
    if 'etape2' not in session:
        return redirect(url_for('etape2'))
    erreur = None
    if request.method == 'POST':
        heures_str    = request.form.get('heures_telephone', '').strip()
        streaming_str = request.form.get('heures_streaming', '').strip()
        apps          = request.form.getlist('apps_utilisees')
        if not heures_str or not streaming_str:
            erreur = "Veuillez remplir tous les champs."
        elif not apps:
            erreur = "Sélectionnez au moins une application."
        else:
            try:
                heures    = float(heures_str)
                streaming = float(streaming_str)
                if not (0 <= heures <= 24) or streaming < 0:
                    raise ValueError
            except ValueError:
                erreur = "Valeurs numériques invalides."
            else:
                e1 = session['etape1']
                e2 = session['etape2']
                reponse = Reponse(
                    niveau_etudes       = e1['niveau_etudes'],
                    appareil            = e1['appareil'],
                    operateur           = e2['operateur'],
                    type_forfait        = e2['type_forfait'],
                    depenses_mensuelles = e2['depenses_mensuelles'],
                    heures_telephone    = heures,
                    heures_streaming    = streaming,
                    apps_utilisees      = ','.join(apps),
                )
                db.session.add(reponse)
                db.session.commit()
                session.pop('etape1', None)
                session.pop('etape2', None)
                return redirect(url_for('succes'))
    return render_template('etape3.html', erreur=erreur)


@app.route('/succes')
def succes():
    return render_template('succes.html')


# --- Dashboard ---

@app.route('/dashboard')
def dashboard():
    reponses = Reponse.query.all()
    total    = len(reponses)

    if total == 0:
        return render_template('dashboard.html', charts=[], stats={}, total=0)

    # Construction du DataFrame
    data = [{
        'niveau_etudes':       r.niveau_etudes,
        'appareil':            r.appareil,
        'operateur':           r.operateur,
        'type_forfait':        r.type_forfait,
        'depenses_mensuelles': r.depenses_mensuelles,
        'heures_telephone':    r.heures_telephone,
        'heures_streaming':    r.heures_streaming,
        'apps_utilisees':      r.apps_utilisees or '',
    } for r in reponses]

    df     = pd.DataFrame(data)
    charts = []

    # Graphique 1 : Histogramme heures d'utilisation
    fig1 = px.histogram(
        df, x='heures_telephone', nbins=12,
        title="⏱ Heures d'utilisation par jour",
        labels={'heures_telephone': 'Heures / jour', 'count': 'Étudiants'},
        color_discrete_sequence=['#00D68F'],
    )
    fig1.update_layout(**LAYOUT_BASE)
    charts.append(to_json(fig1))

    # Graphique 2 : Répartition par opérateur (camembert)
    op_df = df['operateur'].value_counts().reset_index()
    op_df.columns = ['operateur', 'count']
    fig2 = px.pie(
        op_df, values='count', names='operateur',
        title='📶 Répartition par opérateur',
        color_discrete_sequence=['#00D68F', '#00A3FF', '#FF6B6B', '#FFD166'],
    )
    fig2.update_layout(**LAYOUT_BASE)
    charts.append(to_json(fig2))

    # Graphique 3 : Box plot dépenses par niveau d'études
    fig3 = px.box(
        df, x='niveau_etudes', y='depenses_mensuelles',
        title="💰 Dépenses mensuelles par niveau (FCFA)",
        labels={'niveau_etudes': 'Niveau', 'depenses_mensuelles': 'FCFA / mois'},
        color='niveau_etudes',
        color_discrete_sequence=['#00D68F', '#00A3FF', '#FF6B6B', '#FFD166', '#C77DFF'],
    )
    fig3.update_layout(**LAYOUT_BASE, showlegend=False)
    charts.append(to_json(fig3))

    # Graphique 4 : Applications les plus utilisées (barres horizontales)
    app_top_name = 'N/A'
    all_apps = []
    for s in df['apps_utilisees']:
        if s:
            all_apps.extend([a.strip() for a in s.split(',') if a.strip()])
    if all_apps:
        app_df = pd.Series(all_apps).value_counts().reset_index()
        app_df.columns = ['app', 'count']
        app_top_name = app_df.iloc[0]['app']
        fig4 = px.bar(
            app_df, x='count', y='app', orientation='h',
            title='📱 Applications les plus utilisées',
            labels={'count': "Nombre d'étudiants", 'app': ''},
            color='count',
            color_continuous_scale='Teal',
        )
        fig4.update_layout(**LAYOUT_BASE, yaxis={'categoryorder': 'total ascending'})
        charts.append(to_json(fig4))

    # Graphique 5 : Type de forfait
    forfait_df = df['type_forfait'].value_counts().reset_index()
    forfait_df.columns = ['forfait', 'count']
    fig5 = px.bar(
        forfait_df, x='forfait', y='count',
        title='📦 Types de forfait utilisés',
        labels={'forfait': 'Forfait', 'count': 'Étudiants'},
        color='forfait',
        color_discrete_sequence=['#00D68F', '#00A3FF', '#FFD166'],
    )
    fig5.update_layout(**LAYOUT_BASE, showlegend=False)
    charts.append(to_json(fig5))

    # Statistiques descriptives
    stats = {
        'total':         total,
        'moy_heures':    round(df['heures_telephone'].mean(), 1),
        'med_heures':    round(df['heures_telephone'].median(), 1),
        'std_heures':    round(df['heures_telephone'].std(), 1),
        'moy_depenses':  int(df['depenses_mensuelles'].mean()),
        'med_depenses':  int(df['depenses_mensuelles'].median()),
        'moy_streaming': round(df['heures_streaming'].mean(), 1),
        'operateur_top': df['operateur'].value_counts().idxmax(),
        'app_top':       app_top_name,
        'niveau_top':    df['niveau_etudes'].value_counts().idxmax(),
    }

    return render_template('dashboard.html', charts=charts, stats=stats, total=total)


# ─── Entrée ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)

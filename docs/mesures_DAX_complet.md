# 📐 Mesures DAX — Dashboard OEE / TRS
## Projet Big Data · Analyse OEE Ligne de Production

---

## 🔗 Modèle de Données (Schéma en Étoile)

```
         ┌──────────────┐
         │   machines   │ (Dimension)
         └──────┬───────┘
                │ machine_id
    ┌───────────┼───────────┐
    │           │           │
┌───▼────┐  ┌──▼──────┐  ┌─▼──────┐
│ shifts │  │production│  │ arrets │ (Faits)
└────────┘  └──────────┘  └───┬────┘
    (Dim)      (Fait)          │ cause_id
                          ┌────▼──────────┐
                          │ causes_arrets  │ (Dimension)
                          └───────────────┘
```

**Relations :**
- `production[machine_id]` → `machines[machine_id]` (Many to One)
- `production[shift_id]`   → `shifts[shift_id]`     (Many to One)
- `arrets[machine_id]`     → `machines[machine_id]`  (Many to One)
- `arrets[cause_id]`       → `causes_arrets[cause_id]` (Many to One)
- `production[date]`       → `DateTable[Date]`       (Many to One)

---

## 📅 Table de Dates (obligatoire en DAX)

```dax
DateTable = 
ADDCOLUMNS(
    CALENDAR(DATE(2024,1,1), DATE(2024,12,31)),
    "Année",        YEAR([Date]),
    "Mois Num",     MONTH([Date]),
    "Mois Nom",     FORMAT([Date], "MMMM"),
    "Mois Court",   FORMAT([Date], "MMM"),
    "Trimestre",    "T" & QUARTER([Date]),
    "Semaine",      WEEKNUM([Date]),
    "Jour Semaine", FORMAT([Date], "dddd"),
    "Jour Num",     WEEKDAY([Date]),
    "Année-Mois",   FORMAT([Date], "YYYY-MM"),
    "Est Weekend",  IF(WEEKDAY([Date],2) >= 6, TRUE(), FALSE())
)
```

---

## 🔢 Mesures Fondamentales OEE

### 1. Disponibilité (D)
```dax
[Disponibilite] = 
DIVIDE(
    SUMX(production, production[temps_marche_min]),
    SUMX(production, production[temps_requis_min]),
    0
)
```

### 2. Performance (P)
```dax
[Performance] = 
DIVIDE(
    SUMX(production, production[production_reelle]),
    SUMX(production, production[production_theorique]),
    0
)
```

### 3. Qualité (Q)
```dax
[Qualite] = 
DIVIDE(
    SUMX(production, production[production_conforme]),
    SUMX(production, production[production_reelle]),
    0
)
```

### 4. OEE Global ⭐
```dax
[OEE] = [Disponibilite] * [Performance] * [Qualite]
```

### 5. OEE en % formaté
```dax
[OEE %] = FORMAT([OEE], "0.00%")
```

---

## 📊 Mesures de Production

### Total Pièces Produites
```dax
[Total Production] = SUM(production[production_reelle])
```

### Total Pièces Conformes
```dax
[Total Conforme] = SUM(production[production_conforme])
```

### Total Rebuts
```dax
[Total Rebuts] = SUM(production[rebuts])
```

### Taux de Rebut
```dax
[Taux Rebut] = 
DIVIDE([Total Rebuts], [Total Production], 0)
```

### Production Théorique Max
```dax
[Production Theorique] = SUM(production[production_theorique])
```

### Pièces Perdues (Disponibilité)
```dax
[Pieces Perdues Dispo] = 
([Total Production] / [Performance] / [Qualite]) * (1 - [Disponibilite])
```

### Pièces Perdues (Performance)
```dax
[Pieces Perdues Perf] = 
([Total Production] / [Qualite]) * (1 - [Performance])
```

### Pièces Perdues (Qualité)
```dax
[Pieces Perdues Qual] = [Total Rebuts]
```

---

## ⏱ Mesures Temps d'Arrêt

### Total Temps d'Arrêt (minutes)
```dax
[Total Arret Min] = SUM(arrets[duree_minutes])
```

### Total Temps d'Arrêt (heures)
```dax
[Total Arret Heures] = 
DIVIDE([Total Arret Min], 60)
```

### MTBF — Mean Time Between Failures
```dax
[MTBF Heures] = 
VAR NbPannes = COUNTROWS(FILTER(arrets, 
    RELATED(causes_arrets[categorie]) = "Panne"))
RETURN
DIVIDE([Total Arret Heures], NbPannes, 0)
```

### MTTR — Mean Time To Repair
```dax
[MTTR Heures] = 
VAR PannesOnly = FILTER(arrets, 
    RELATED(causes_arrets[categorie]) = "Panne")
RETURN
DIVIDE(
    SUMX(PannesOnly, PannesOnly[duree_minutes]),
    COUNTROWS(PannesOnly),
    0
) / 60
```

### Temps d'Arrêt par Cause
```dax
[Arret par Cause] = SUM(arrets[duree_minutes])
```

### % Contribution Arrêt (Pareto)
```dax
[% Contribution Arret] = 
DIVIDE(
    SUM(arrets[duree_minutes]),
    CALCULATE(SUM(arrets[duree_minutes]), ALL(causes_arrets)),
    0
)
```

### % Cumulé Arrêt (Courbe Pareto)
```dax
[% Cumule Arret] = 
VAR CurrentCause = MAX(causes_arrets[description])
VAR CurrentVal = CALCULATE(SUM(arrets[duree_minutes]))
VAR TotalAll = CALCULATE(SUM(arrets[duree_minutes]), ALL(causes_arrets))
RETURN
DIVIDE(
    SUMX(
        FILTER(
            ALL(causes_arrets),
            CALCULATE(SUM(arrets[duree_minutes])) >= CurrentVal
        ),
        CALCULATE(SUM(arrets[duree_minutes]))
    ),
    TotalAll, 0
)
```

---

## 📈 Mesures Temporelles & Comparaisons

### OEE Mois Précédent
```dax
[OEE Mois Prec] = 
CALCULATE([OEE], DATEADD(DateTable[Date], -1, MONTH))
```

### Variation OEE vs Mois Précédent
```dax
[Delta OEE Mois] = [OEE] - [OEE Mois Prec]
```

### OEE Année Précédente
```dax
[OEE An Prec] = 
CALCULATE([OEE], SAMEPERIODLASTYEAR(DateTable[Date]))
```

### OEE YTD (Cumul Année)
```dax
[OEE YTD] = 
CALCULATE([OEE], DATESYTD(DateTable[Date]))
```

### OEE Moyenne Glissante 3 Mois
```dax
[OEE MA 3M] = 
CALCULATE([OEE], DATESINPERIOD(DateTable[Date], LASTDATE(DateTable[Date]), -3, MONTH))
```

---

## 🎯 Mesures de Performance vs Objectifs

### Objectif OEE (paramètre)
```dax
[Objectif OEE] = 0.85
```

### Gap vs Objectif
```dax
[Gap OEE Objectif] = [OEE] - [Objectif OEE]
```

### Statut OEE (texte dynamique)
```dax
[Statut OEE] = 
SWITCH(
    TRUE(),
    [OEE] >= 0.85, "🏆 World Class",
    [OEE] >= 0.70, "✅ Bon",
    [OEE] >= 0.60, "⚠ À améliorer",
    "🔴 Critique"
)
```

### Couleur OEE (pour formatage conditionnel)
```dax
[Couleur OEE] = 
SWITCH(
    TRUE(),
    [OEE] >= 0.85, "#10b981",   -- Vert
    [OEE] >= 0.70, "#3b82f6",   -- Bleu
    [OEE] >= 0.60, "#f59e0b",   -- Orange
    "#ef4444"                    -- Rouge
)
```

### Gain Potentiel Production (si OEE → 85%)
```dax
[Gain Potentiel Pieces] = 
([Objectif OEE] - [OEE]) * [Production Theorique]
```

---

## 🏭 Mesures par Machine (Ranking)

### Rang OEE Machine
```dax
[Rang OEE Machine] = 
RANKX(ALL(machines[machine_id]), [OEE], , DESC, DENSE)
```

### Meilleure Machine OEE
```dax
[Meilleure Machine] = 
CALCULATE(
    MAX(machines[nom_machine]),
    FILTER(machines, [OEE] = MAXX(ALL(machines), [OEE]))
)
```

### OEE Machine la Plus Faible
```dax
[OEE Min Machine] = MINX(ALL(machines[machine_id]), [OEE])
```

---

## 📋 KPIs Cartes Résumé

### Texte Résumé Global
```dax
[Resume Performance] = 
"OEE Global : " & FORMAT([OEE], "0.0%") & 
" | D: " & FORMAT([Disponibilite], "0.0%") & 
" | P: " & FORMAT([Performance], "0.0%") & 
" | Q: " & FORMAT([Qualite], "0.0%")
```

### Alerte Machine Critique
```dax
[Nb Machines Critiques] = 
COUNTX(
    FILTER(ALL(machines[machine_id]), [OEE] < 0.65),
    machines[machine_id]
)
```

---

## 💡 Conseils d'Implémentation Power BI

### Format des mesures %
→ Toutes les mesures D, P, Q, OEE → Format : `0.0%`

### Pages recommandées
1. **Vue Globale** → KPI Cards + Courbe tendance
2. **Disponibilité** → Pareto causes + Heatmap
3. **Machines** → Tableau comparatif + Barres
4. **Drill-through** → Fiche machine détaillée

### Filtres (Slicers) à ajouter
- Période (mois/trimestre)
- Machine (multi-sélection)
- Ligne de production
- Équipe (shift)

### Formatage conditionnel
- OEE ≥ 85% → `#10b981` (vert)
- OEE 70-84% → `#3b82f6` (bleu)
- OEE 60-69% → `#f59e0b` (orange)
- OEE < 60%  → `#ef4444` (rouge)

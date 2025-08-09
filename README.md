# LOG430 – Laboratoire 6 : Saga Orchestrée Synchrone et Machine d’État

## Présentation
Ce laboratoire prolonge les Labos 4 et 5 en ajoutant une Saga orchestrée synchrone centralisée pour coordonner une transaction distribuée entre microservices. Un nouveau service `service-saga-orchestrator` orchestre les appels aux services via Kong, maintient une machine d’état explicite et expose des métriques Prometheus visualisées dans Grafana.

## Scénario métier implémenté
- Vérification du stock (service-inventaire via Kong)
- Récupération des informations produit (service-catalogue via Kong)
- Réservation du stock (service-inventaire)
- Création de la commande (service-commandes)
- Compensation en cas d’échec (libération du stock réservé)

Machine d’état détaillée: `docs/UML/saga-state-machine.puml` (PlantUML). Pour générer l’image:
```bash
java -jar plantuml.jar -o out/docs/UML docs/UML/saga-state-machine.puml
```

## Périmètre applicatif
- Microservices: `service-catalogue` (3 instances, load-balanced), `service-inventaire`, `service-commandes`, `service-supply-chain`, `service-ecommerce`.
- Orchestrateur: `service-saga-orchestrator` (Django REST + DDD).
- API Gateway: Kong (routage, clé API, Prometheus, file-log, CORS).
- Observabilité: Prometheus, Grafana, logs structurés JSON.

## Déploiement
Pré-requis: Docker + Docker Compose, ports libres: 80, 8001–8007, 8009, 8080–8081, 5433–5439, 6379, 9090, 3000.

```bash
docker-compose up --build -d
```

Notes:
- La configuration Kong (upstreams, routes, plugins CORS, key-auth, Prometheus, consommateur et clé API) est provisionnée automatiquement par `scripts/setup-kong.sh` (service `kong-setup`).
- Les migrations et jeux de données initiaux des services sont lancés au démarrage (voir `docker-compose.yml`).

Accès:
- Kong API Gateway: http://localhost:8080 (proxy), http://localhost:8081 (admin)
- Service Saga Orchestrator: http://localhost:8009
- Catalogue: http://localhost:8001, 8006, 8007
- Inventaire: http://localhost:8002
- Commandes: http://localhost:8003
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

Clé API Kong (header requis): `X-API-Key: magasin-secret-key-2025`

## API du Service Saga Orchestrator
Base: `http://localhost:8009`

- POST `/api/saga/commandes/` — Démarrer une saga de commande
  Exemple:
  ```bash
  curl -X POST http://localhost:8009/api/saga/commandes/ \
    -H 'Content-Type: application/json' \
    -d '{
      "client_id": "12345678-1234-1234-1234-123456789012",
      "magasin_id": "550e8400-e29b-41d4-a716-446655440000",
      "lignes": [{
        "produit_id": "550e8400-e29b-41d4-a716-446655440001",
        "quantite": 1
      }]
    }'
  ```
- GET `/api/saga/commandes/{saga_id}/` — Consulter une saga (statut + historique)
- GET `/api/saga/sagas/?etat=...&actives_seulement=true` — Lister/filtrer les sagas
- POST `/api/saga/commandes/{saga_id}/compenser/` — Forcer la compensation d’une saga orpheline
- GET `/api/saga/health/` — Health check
- GET `/metrics/` — Exposition Prometheus du service saga

Orchestration côté code: `service-saga-orchestrator/application/saga_orchestrator.py` (classe `SagaOrchestrator`). Machine d’état et événements: `service-saga-orchestrator/domain/entities.py`.

## Observabilité
- Métriques Prometheus implémentées: `service-saga-orchestrator/infrastructure/prometheus_metrics.py`
  - `saga_total`, `saga_duree_seconds`, `saga_echecs_total`, `saga_etapes_total`, `saga_compensations_total`
  - `services_externes_calls_total`, `services_externes_duree_seconds`
- Scrape Prometheus: job `saga-orchestrator` vers `service-saga-orchestrator:8009/metrics` (voir `config/prometheus.yml`).
- Dashboard Grafana provisionné: `config/grafana/provisioning/dashboards/saga-observability.json`
  - P50/P95/Moyenne durées de saga, taux de démarrage, répartition des étapes, nombre de compensations, progression par statut.
- Logs structurés JSON activés (niveau INFO par défaut).

## Tests et cas d’échec simulés
Script d’intégration: `test_saga_integration.py`.

```bash
# Lancer les tests d’intégration du service saga
python test_saga_integration.py

# Succès rapide (stock dispo, 1 produit)
curl -X POST http://localhost:8009/api/saga/commandes/ \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "12345678-1234-1234-1234-123456789012",
    "magasin_id": "550e8400-e29b-41d4-a716-446655440000",
    "lignes": [{"produit_id": "550e8400-e29b-41d4-a716-446655440001", "quantite": 1}]
  }'

# Échec contrôlé – stock insuffisant (quantité très élevée)
curl -X POST http://localhost:8009/api/saga/commandes/ \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "12345678-1234-1234-1234-123456789012",
    "magasin_id": "550e8400-e29b-41d4-a716-446655440000",
    "lignes": [{"produit_id": "550e8400-e29b-41d4-a716-446655440001", "quantite": 1000}]
  }'

# Consulter la saga
curl http://localhost:8009/api/saga/commandes/{saga_id}/
```

Cas d’échec gérés et compensation:
- ECHEC_STOCK_INSUFFISANT: annulation directe (pas de stock réservé).
- ECHEC_RESERVATION_STOCK: annulation (réservations partielles libérées si nécessaire).
- ECHEC_CREATION_COMMANDE: compensation obligatoire puis annulation (POST augmenter-stock/).

## Décisions d’architecture (ADR)
- ADR-001 — Pattern Saga Orchestrée Synchrone: `docs/ADR/ADR-001.md`
- ADR-002 — Observabilité multi-niveaux: `docs/ADR/ADR-002.md`

## Structure du dépôt (extrait)
```plaintext
service-saga-orchestrator/
├── application/saga_orchestrator.py      # Orchestrateur (Kong + sync calls)
├── domain/entities.py                    # Machine d’état, événements, entités
├── interfaces/saga_api.py                # Endpoints REST + /metrics
├── infrastructure/django_saga_repository.py  # Persistance (PostgreSQL)
└── infrastructure/prometheus_metrics.py  # Compteurs/Histogrammes/Gauges
```

## Dépannage
- Si les appels vers `kong:8080` échouent (connection refused), attendre que `kong` et `kong-setup` terminent, puis relancer la requête.
- Vérifier la clé API dans vos appels via Kong: `-H 'X-API-Key: magasin-secret-key-2025'`.
- Logs orchestrateur: `docker-compose logs -f service-saga-orchestrator | cat`
- Métriques: http://localhost:8009/metrics et panneau Grafana “Observabilité des Sagas - LOG430 Lab6”.

## Auteurs
Labo réalisé dans le cadre du cours LOG430 – Été 2025.

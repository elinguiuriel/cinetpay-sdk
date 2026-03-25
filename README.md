# CinetPay Python SDK

SDK Python minimaliste pour le nouvel API CinetPay, basé sur la documentation sandbox fournie.

Base URL sandbox par défaut: `https://api.cinetpay.net`

## Harness Engineering

Le dépôt suit désormais une approche "harness-first" inspirée de l'article OpenAI "Harness engineering":

- le dépôt contient ses règles de fonctionnement dans [AGENTS.md](AGENTS.md)
- le contrat externe CinetPay est synthétisé dans `docs/cinetpay-sandbox-contract.md`
- les comportements critiques sont encodés dans des scénarios exécutables sous `harness/scenarios/`
- l'architecture est vérifiée mécaniquement par des tests structurels
- une boucle courte `python scripts/run_quality.py` sert de porte d'entrée unique

Commandes principales:

```bash
python scripts/run_harness.py
python scripts/run_quality.py
```

Sources de vérité du dépôt:

- `AGENTS.md`
- `docs/architecture.md`
- `docs/cinetpay-sandbox-contract.md`
- `harness/scenarios/*.json`

## Fonctionnalités

- Authentification OAuth via `POST /v1/oauth/login`
- Initialisation de paiement web via `POST /v1/payment`
- Consultation du statut d'un paiement via `GET /v1/payment/{identifier}`
- Création de transfert via `POST /v1/transfer`
- Consultation du statut d'un transfert via `GET /v1/transfer/{transaction_id}`
- Consultation du solde via `GET /v1/balances`
- Validation simple des notifications `notify_token`
- Rafraîchissement automatique du token si l'API retourne `1003 EXPIRED_TOKEN`

## Installation

```bash
pip install .
```

Pour le développement:

```bash
pip install -e .[dev]
```

## Structure du SDK

Le package expose principalement:

- `CinetPayClient`
- `PaymentRequest`
- `TransferRequest`
- `PaymentResponse`
- `PaymentStatusResponse`
- `TransferResponse`
- `BalanceResponse`

## Exemple rapide

```python
from cinetpay_sdk import CinetPayClient, PaymentRequest

client = CinetPayClient(
    api_key="your-account-key",
    api_password="your-account-password",
)

payment = client.create_payment(
    PaymentRequest(
        currency="XOF",
        payment_method="OM",
        merchant_transaction_id="ORDER-1001",
        amount=1000,
        lang="fr",
        designation="Paiement abonnement",
        client_email="client@example.com",
        client_first_name="Jean",
        client_last_name="Doe",
        client_phone_number="+2250707070700",
        success_url="https://merchant.test/payment/success",
        failed_url="https://merchant.test/payment/failed",
        notify_url="https://merchant.test/payment/notify",
    )
)

print(payment.payment_token)
print(payment.payment_url)
print(payment.details.status if payment.details else None)

if payment.should_redirect:
    print("Rediriger le client vers:", payment.payment_url)
```

## Authentification

Le client s'authentifie automatiquement au premier appel protégé.

Vous pouvez aussi forcer l'authentification:

```python
token = client.authenticate()
print(token.access_token)
```

Vous pouvez aussi charger les identifiants depuis les variables d'environnement:

```python
from cinetpay_sdk import CinetPayClient

client = CinetPayClient.from_env()
```

Variables utilisées:

- `CINETPAY_API_KEY`
- `CINETPAY_API_PASSWORD`
- `CINETPAY_BASE_URL` optionnelle

## Paiement web

```python
status = client.get_payment_status("payment-token-or-transaction-id")
print(status.status)
```

La documentation fournie indique que l'identifiant accepté peut être:

- `payment_token`
- `transaction_id`
- `merchant_transaction_id`

Le SDK transmet simplement la valeur dans l'URL `GET /v1/payment/{identifier}`.

## Paiement direct

Le SDK vous laisse activer `direct_pay=True`. Dans ce cas, `client_phone_number` devient obligatoire.

```python
payment = client.create_payment(
    PaymentRequest(
        currency="XOF",
        payment_method="OM",
        merchant_transaction_id="ORDER-1002",
        amount=500,
        lang="fr",
        designation="Paiement direct",
        client_email="client@example.com",
        client_first_name="Jean",
        client_last_name="Doe",
        client_phone_number="+2250707070701",
        success_url="https://merchant.test/success",
        failed_url="https://merchant.test/failed",
        notify_url="https://merchant.test/notify",
        direct_pay=True,
        otp_code="1234",
    )
)

if payment.details:
    print(payment.details.status)
    print(payment.details.message)
```

## Transferts

```python
from cinetpay_sdk import TransferRequest

transfer = client.create_transfer(
    TransferRequest(
        currency="XOF",
        payment_method="OM_CI",
        merchant_transaction_id="TRANSFER-1001",
        amount=100,
        phone_number="+2250707000001",
        reason="Rechargement de compte",
        notify_url="https://merchant.test/transfer/notify",
    )
)

print(transfer.status)
print(transfer.transaction_id)
```

Puis:

```python
transfer_status = client.get_transfer_status(transfer.transaction_id)
print(transfer_status.status)
```

## Solde

Le format détaillé de réponse n'est pas documenté dans le contenu fourni. Le SDK retourne donc:

- `code`
- `status`
- `balances`: toutes les autres clés de la réponse

```python
balances = client.get_balances()
print(balances.status)
print(balances.balances)
```

## Notifications

Exemple de validation d'un `notify_token` reçu via votre endpoint:

```python
from cinetpay_sdk import CinetPayClient

payload = {
    "notify_token": "4bbd93ce1824ca005b8df92069a6b56cca005b8",
    "merchant_transaction_id": "63e0fe766f390",
    "transaction_id": "50901a80c84b4edcb4f50ae864bfa7c5",
    "user": {
        "name": "Jaqn HGHAR",
        "email": "jaqen@gmail.com",
        "phone_number": "+2250700356615",
    },
}

if CinetPayClient.validate_notification(payload, expected_notify_token="4bbd93ce1824ca005b8df92069a6b56cca005b8"):
    notification = CinetPayClient.parse_notification(payload)
    payment_status = client.get_payment_status(notification.transaction_id)
```

Bon usage côté serveur:

- conservez le `notify_token` reçu lors de l'initialisation
- comparez-le à celui reçu dans la notification POST
- vérifiez ensuite le statut final auprès de l'API CinetPay

## Exceptions

Le SDK expose:

- `CinetPayError`
- `APIError`
- `AuthenticationError`
- `ValidationError`
- `NetworkError`

Exemple:

```python
from cinetpay_sdk import APIError, CinetPayClient, NetworkError

try:
    balances = client.get_balances()
except NetworkError as exc:
    print("Erreur réseau:", exc)
except APIError as exc:
    print("Erreur API:", exc.code, exc.status, exc.payload)
```

## Numéros de test sandbox

D'après la documentation fournie:

- Côte d'Ivoire succès immédiat: `+2250707070700`
- Côte d'Ivoire pending puis succès: `+2250707070701`
- Côte d'Ivoire échec immédiat: `+2250707070703`
- Côte d'Ivoire pending puis échec: `+2250707070704`
- Côte d'Ivoire pending infini: `+2250707070706`
- Transfert sandbox: `+2250707000001`

## Hypothèses prises dans cette première version

- Le bearer token est envoyé dans l'en-tête `Authorization: Bearer <token>`
- Le endpoint `GET /v1/payment/{identifier}` accepte les identifiants décrits dans la documentation fournie
- Le format détaillé de `GET /v1/balances` n'étant pas documenté dans votre extrait, il est conservé de manière flexible

## Développement local

```bash
python scripts/run_quality.py
```

Si vous voulez uniquement exécuter les tests:

```bash
python -m unittest discover -s tests -v
```

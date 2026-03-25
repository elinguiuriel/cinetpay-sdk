# Sandbox Testing Tools

This repository includes a manual sandbox CLI to exercise the real CinetPay
sandbox with your own credentials.

CLI entry point:

- `python scripts/sandbox_cli.py`

## Supported Commands

- `env-check`
- `auth`
- `balances`
- `payment`
- `payment-status`
- `transfer`
- `transfer-status`

## Before You Start

1. Configure `CINETPAY_API_KEY` and `CINETPAY_API_PASSWORD`
2. Optionally create `.env` from `.env.example`
3. Ensure you are targeting the sandbox base URL

Quick verification:

```bash
python scripts/sandbox_cli.py env-check
python scripts/sandbox_cli.py auth
```

## Example Payment Test

Web payment:

```bash
python scripts/sandbox_cli.py payment \
  --amount 100 \
  --payment-method OM \
  --client-phone +2250707070700 \
  --success-url https://example.com/payment/success \
  --failed-url https://example.com/payment/failed \
  --notify-url https://webhook.site/replace-me
```

Direct pay:

```bash
python scripts/sandbox_cli.py payment \
  --amount 100 \
  --payment-method OM \
  --direct-pay \
  --otp-code 1234 \
  --client-phone +2250707070700 \
  --success-url https://example.com/payment/success \
  --failed-url https://example.com/payment/failed \
  --notify-url https://webhook.site/replace-me
```

Check the status later:

```bash
python scripts/sandbox_cli.py payment-status --identifier <payment_token_or_transaction_id>
```

## Example Transfer Test

The provided CinetPay sandbox documentation uses `+2250707000001` for transfer
tests.

```bash
python scripts/sandbox_cli.py transfer \
  --amount 100 \
  --payment-method OM_CI \
  --phone-number +2250707000001 \
  --notify-url https://webhook.site/replace-me
```

Then:

```bash
python scripts/sandbox_cli.py transfer-status --transaction-id <transaction_id>
```

## Test Numbers

Useful numbers from the repository contract:

- immediate success: `+2250707070700`
- pending then success: `+2250707070701`
- immediate failure: `+2250707070703`
- pending then failure: `+2250707070704`
- infinite pending: `+2250707070706`
- transfer sandbox number: `+2250707000001`

## Output Format

The CLI prints JSON suitable for copying into bug reports or test notes.
Sensitive credentials are never printed in full.

## Transport Note

The sandbox currently rejects the default `Python-urllib/x.y` user-agent with a
Cloudflare `Error 1010: browser_signature_banned`.

The repository transport therefore sends a dedicated SDK user-agent by default.
If you replace the transport layer in your own application, keep that in mind.

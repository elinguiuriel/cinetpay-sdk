# Secure Credential Setup

This document explains how to configure CinetPay sandbox credentials without
leaking them into source control, shell history, or CI logs.

## Variables Used By The SDK

The SDK and sandbox tools read these variables:

- `CINETPAY_API_KEY`
- `CINETPAY_API_PASSWORD`
- `CINETPAY_BASE_URL` optional, defaults to `https://api.cinetpay.net`

The sandbox CLI can also use these optional defaults:

- `CINETPAY_SUCCESS_URL`
- `CINETPAY_FAILED_URL`
- `CINETPAY_NOTIFY_URL`
- `CINETPAY_TEST_CLIENT_EMAIL`

## Local Development

Preferred approach:

1. Copy `.env.example` to `.env`
2. Replace the placeholder values
3. Keep `.env` local only

The repository ignores `.env` and `.env.*` by default. `.env.example` remains
tracked because it contains placeholders only.

Example:

```bash
cp .env.example .env
chmod 600 .env
```

Then edit `.env`:

```dotenv
CINETPAY_API_KEY=your-real-account-key
CINETPAY_API_PASSWORD=your-real-account-password
CINETPAY_BASE_URL=https://api.cinetpay.net
```

The `chmod 600` step ensures only your user can read the file on a shared
machine.

## Shell Export Alternative

If you prefer not to use a local `.env` file:

```bash
export CINETPAY_API_KEY='your-real-account-key'
export CINETPAY_API_PASSWORD='your-real-account-password'
export CINETPAY_BASE_URL='https://api.cinetpay.net'
```

This is acceptable for temporary sessions but less convenient for repeatable
local testing.

## CI And Deployment

Never store real CinetPay credentials in:

- committed files
- Dockerfiles
- application settings checked into Git
- GitHub Actions workflow YAML

Use your deployment platform secret store instead.

For GitHub Actions:

1. Open repository settings
2. Go to `Secrets and variables`
3. Create `Actions` secrets named `CINETPAY_API_KEY` and `CINETPAY_API_PASSWORD`
4. Reference them as environment variables in the workflow

Example:

```yaml
env:
  CINETPAY_API_KEY: ${{ secrets.CINETPAY_API_KEY }}
  CINETPAY_API_PASSWORD: ${{ secrets.CINETPAY_API_PASSWORD }}
```

## Logging Rules

Do not log:

- raw `CINETPAY_API_KEY`
- raw `CINETPAY_API_PASSWORD`
- full bearer tokens returned by the OAuth endpoint

If you must confirm which secret is loaded, print a masked form only, such as:

- `abcd...wxyz`

The sandbox CLI included in this repository follows that rule.

## Rotation

If a credential is exposed:

1. rotate it in CinetPay immediately
2. update the local `.env` or your secret store
3. check recent commits and CI logs for accidental exposure

## Repository Rule

If a future change introduces a new credential, document it here and keep the
secret-bearing file ignored by Git.

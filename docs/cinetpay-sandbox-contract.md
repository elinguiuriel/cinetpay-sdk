# CinetPay Sandbox Contract

This file is the repository-level contract for the current SDK behavior derived from the CinetPay sandbox documentation provided by the repository owner.

Base URL:

- `https://api.cinetpay.net`

## Authentication

Endpoint:

- `POST /v1/oauth/login`

Request body:

- `api_key`
- `api_password`

Expected successful response shape:

- `code = 200`
- `status = OK`
- `access_token`
- `token_type`
- `expires_in`

Repository assumption:

- the token is sent as `Authorization: Bearer <access_token>`
- if the API returns `1003 EXPIRED_TOKEN`, the client re-authenticates once and retries the request

## Payments

Endpoint:

- `POST /v1/payment`

The SDK currently models these request fields:

- `currency`
- `payment_method`
- `merchant_transaction_id`
- `amount`
- `lang`
- `designation`
- `client_email`
- `client_phone_number`
- `client_first_name`
- `client_last_name`
- `direct_pay`
- `otp_code`
- `success_url`
- `failed_url`
- `notify_url`

Local SDK validation:

- `merchant_transaction_id` length must be `<= 30`
- `lang` must be `fr` or `en`
- `amount` must be `> 0`
- `client_first_name` and `client_last_name` must contain between 2 and 255 characters
- `success_url`, `failed_url`, `notify_url` must be valid URLs and `<= 120` chars
- `client_phone_number` is required when `direct_pay = true`
- `otp_code`, if provided, must contain 4 to 6 digits

Response handling rules:

- `details.must_be_redirected = true` and a non-empty `payment_url` means `PaymentResponse.should_redirect == True`
- `details.status in {SUCCESS, FAILED}` means the payment response is final

Payment status endpoint:

- `GET /v1/payment/{identifier}`

Repository assumption:

- the API accepts `payment_token`, `transaction_id`, or `merchant_transaction_id` as the path identifier because that is what the provided documentation states

## Transfers

Endpoint:

- `POST /v1/transfer`

Modeled request fields:

- `currency`
- `payment_method`
- `merchant_transaction_id`
- `amount`
- `phone_number`
- `reason`
- `notify_url`

Transfer status endpoint:

- `GET /v1/transfer/{transaction_id}`

Response handling rule:

- `status in {SUCCESS, FAILED}` means the transfer is final

## Balances

Endpoint:

- `GET /v1/balances`

The provided documentation did not specify a complete response shape. The SDK therefore treats:

- `code`
- `status`

as reserved fields and stores all remaining keys in `BalanceResponse.balances`.

## Notifications

Notification handling rule:

- validate the received `notify_token` against the `notify_token` returned during payment or transfer initialization
- then query the final status from the API

## Status Codes Relevant To The SDK

- `200 OK`
- `100 SUCCESS`
- `1002 INVALID_TOKEN`
- `1003 EXPIRED_TOKEN`
- `1004 INVALID_PARAMS`
- `1005 INVALID_CREDENTIALS`
- `2010 FAILED`
- `2011 NOT_ALLOWED`

The SDK maps:

- `1002`, `1003`, `1005` to authentication errors
- `1004` and HTTP `422` to validation errors

## Harness Acceptance Scenarios

The repository harness must continuously validate these cases:

1. web payment initialization that requires redirect
2. direct payment initialization that ends in `FAILED` without redirect
3. payment status request that retries after `EXPIRED_TOKEN`
4. successful transfer initialization
5. balance response with flexible payload shape

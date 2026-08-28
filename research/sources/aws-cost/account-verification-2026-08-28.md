# AWS account verification

Verified through authenticated, read-only AWS CLI calls on 2026-08-28.
The account identifier is intentionally omitted from this artifact.

## Commands and material results

### `aws freetier get-account-plan-state --region us-east-1`

- Plan type: `PAID`
- Plan status: `ACTIVE`
- Remaining credits: `USD 160.00`

### `aws billing get-credits ... --region us-east-1`

- `AWS Free Tier`: initial `USD 100.00`, remaining `USD 100.00`, expires
  `2027-08-25T19:51:26-03:00`.
- `Explore AWS: Create a web app using AWS Lambda`: initial `USD 20.00`,
  remaining `USD 20.00`, expires `2027-08-25T19:52:02-03:00`.
- Two additional activity credits of `USD 20.00` each appeared after the RDS
  deployment. The authenticated total is therefore `USD 160.00`.
- The initial `USD 100.00` credit and the first `USD 20.00` credit explicitly
  included `Amazon Relational Database Service` in `applicableProductNames`.

### `aws rds describe-db-instances --region us-east-1`

- Instance `vigilante-fase5`: `available`.
- PostgreSQL `16.15`, class `db.t4g.micro`, Single-AZ in `us-east-1b`.
- `20 GiB` gp3, encrypted, public endpoint, no automated backup retention.
- Parameter group `vigilante-fase5-pg16` enforces TLS.
- Security group ingress is limited to the current public IP in `/32`.

### Application and database validation

- Alembic reached revision `0005`.
- PostgreSQL negotiated TLS and loaded `pgvector 0.8.2`.
- The schema contains 13 application tables.
- `/healthz` returned HTTP 200 and `/readyz` reported database and model ready.
- A replay created a pending alert, and the same camera and alert remained
  available after the backend container restarted.

### `aws billing get-credit-allocation-history ...`

- Result: empty allocation history, `partialResults: false`.

### `aws ce get-cost-and-usage ...`

- Result: `DataUnavailableException`. Cost Explorer does not yet have ingested
  data for this newly created account, so it cannot independently confirm the
  current-month zero shown by the Credits API.

### `aws freetier get-account-activity ...`

- The RDS deployment completed two eligible learning activities, explaining
  the increase from the earlier console screenshot of `USD 120.00` to the
  authenticated API total of `USD 160.00`.

## Official API references

- https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html
- https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html
- https://docs.aws.amazon.com/cli/latest/reference/billing/get-credit-allocation-history.html
- https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html
- https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-activity.html

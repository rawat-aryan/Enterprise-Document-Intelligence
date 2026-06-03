-- Contract Risk View
CREATE OR REPLACE VIEW `{project}.{dataset}.contract_risk_view` AS
SELECT
  contract_id,
  contract_type,
  effective_date,
  expiration_date,
  contract_value,
  risk_score,
  DATE_DIFF(expiration_date, CURRENT_DATE(), DAY) AS days_to_expiry,
  CASE
    WHEN DATE_DIFF(expiration_date, CURRENT_DATE(), DAY) < 0 THEN 'expired'
    WHEN DATE_DIFF(expiration_date, CURRENT_DATE(), DAY) <= 30 THEN 'critical'
    WHEN DATE_DIFF(expiration_date, CURRENT_DATE(), DAY) <= 60 THEN 'warning'
    ELSE 'active'
  END AS expiry_status,
  CASE
    WHEN risk_score >= 0.8 THEN 'high'
    WHEN risk_score >= 0.5 THEN 'medium'
    ELSE 'low'
  END AS risk_level,
  tenant_id
FROM `{project}.{dataset}.fact_contracts`
WHERE expiration_date IS NOT NULL;

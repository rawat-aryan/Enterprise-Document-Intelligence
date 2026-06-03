-- Spend Analytics View
CREATE OR REPLACE VIEW `{project}.{dataset}.spend_analytics_view` AS
SELECT
  DATE_TRUNC(invoice_date, MONTH) AS month,
  tenant_id,
  currency,
  COUNT(*) AS invoice_count,
  SUM(total_amount) AS total_spend,
  SUM(tax_amount) AS total_tax,
  AVG(total_amount) AS avg_spend,
  MAX(total_amount) AS max_invoice,
  COUNTIF(is_duplicate) AS duplicates,
  SUM(CASE WHEN is_duplicate THEN total_amount ELSE 0 END) AS duplicate_amount_at_risk
FROM `{project}.{dataset}.fact_invoices`
WHERE invoice_date IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY month DESC;

-- Vendor Performance View
CREATE OR REPLACE VIEW `{project}.{dataset}.vendor_performance_view` AS
SELECT
  vendor_name,
  COUNT(DISTINCT invoice_id) AS total_invoices,
  SUM(total_amount) AS total_spend,
  AVG(total_amount) AS avg_invoice_value,
  MIN(invoice_date) AS first_invoice_date,
  MAX(invoice_date) AS last_invoice_date,
  COUNTIF(is_duplicate) AS duplicate_count,
  SAFE_DIVIDE(COUNTIF(is_duplicate), COUNT(*)) AS duplicate_rate,
  COUNTIF(validation_status = 'valid') AS valid_invoices,
  COUNTIF(validation_status = 'invalid') AS invalid_invoices,
  AVG(confidence_score) AS avg_confidence,
  tenant_id
FROM `{project}.{dataset}.fact_invoices`
WHERE vendor_name IS NOT NULL
GROUP BY vendor_name, tenant_id;

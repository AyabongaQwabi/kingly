-- Allow document type 'app_description'
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_type_check;
ALTER TABLE documents ADD CONSTRAINT documents_type_check
  CHECK (type IN ('app_description', 'business_logic', 'prd', 'prompts', 'upload'));

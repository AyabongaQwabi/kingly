-- Allow document types for Cursor execution package
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_type_check;
ALTER TABLE documents ADD CONSTRAINT documents_type_check
  CHECK (
    type IN (
      'app_description',
      'business_logic',
      'prd',
      'prompts',
      'upload',
      'tech_stack',
      'cursor_rules',
      'cursor_master_prompt',
      'cursor_execution_plan'
    )
  );


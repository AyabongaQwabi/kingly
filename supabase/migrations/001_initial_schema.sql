-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Profiles (optional sync from auth.users)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects: one per user
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);

-- Documents: business_logic, prd, prompts, upload
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('business_logic', 'prd', 'prompts', 'upload')),
  title TEXT NOT NULL,
  content TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_project_type ON documents(project_id, type);

-- Document embeddings for RAG (pgvector)
-- Gemini text-embedding-004 uses 768 dimensions; adjust if using another model
CREATE TABLE IF NOT EXISTS document_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(768),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id ON document_embeddings(document_id);

-- HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding ON document_embeddings
  USING hnsw (embedding vector_cosine_ops);

-- RLS: users can only access their own projects and related documents
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD own projects"
  ON projects FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can CRUD documents in own projects"
  ON documents FOR ALL
  USING (
    EXISTS (SELECT 1 FROM projects p WHERE p.id = documents.project_id AND p.user_id = auth.uid())
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM projects p WHERE p.id = documents.project_id AND p.user_id = auth.uid())
  );

CREATE POLICY "Users can CRUD embeddings for own documents"
  ON document_embeddings FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM documents d
      JOIN projects p ON p.id = d.project_id
      WHERE d.id = document_embeddings.document_id AND p.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM documents d
      JOIN projects p ON p.id = d.project_id
      WHERE d.id = document_embeddings.document_id AND p.user_id = auth.uid()
    )
  );

-- RPC for vector similarity search (called with service role or authenticated user)
CREATE OR REPLACE FUNCTION match_document_embeddings(
  query_embedding vector(768),
  match_count INT DEFAULT 5,
  filter_project_id UUID DEFAULT NULL
)
RETURNS TABLE (
  document_id UUID,
  chunk_index INT,
  content TEXT,
  similarity FLOAT
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    de.document_id,
    de.chunk_index,
    de.content,
    1 - (de.embedding <=> query_embedding) AS similarity
  FROM document_embeddings de
  JOIN documents d ON d.id = de.document_id
  WHERE (filter_project_id IS NULL OR d.project_id = filter_project_id)
    AND de.embedding IS NOT NULL
  ORDER BY de.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Storage bucket: create via Supabase Dashboard or API; RLS by user_id/project_id path
-- project-uploads/{user_id}/{project_id}/{filename}

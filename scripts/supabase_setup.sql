-- 1. Habilitar la extensión pgvector en Supabase
create extension if not exists vector;

-- 2. Crear tabla para guardar fragmentos de conocimiento, metadatos y vectores
create table if not exists documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- 3. Crear índice IVFFlat o HNSW para acelerar la búsqueda vectorial (Opcional pero recomendado)
create index if not exists documents_embedding_idx 
on documents 
using hnsw (embedding vector_cosine_ops);

-- 4. Crear la función RPC match_documents para realizar búsqueda por similitud coseno
create or replace function match_documents (
  query_embedding vector(1536),
  match_count int DEFAULT 4,
  filter jsonb DEFAULT '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;

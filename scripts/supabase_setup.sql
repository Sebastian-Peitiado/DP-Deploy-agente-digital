-- 1. Habilitar la extensión pgvector en Supabase
create extension if not exists vector;

-- 2. Crear tabla para guardar fragmentos de conocimiento, metadatos y vectores
create table if not exists documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- Habilitar RLS (Row Level Security) por seguridad
alter table documents enable row level security;

-- Permitir lectura y escritura pública para la ingesta y consultas
create policy "Permitir lectura publica" 
on documents for select 
to anon, authenticated, service_role 
using (true);

create policy "Permitir insercion publica" 
on documents for insert 
to anon, authenticated, service_role 
with check (true);

create policy "Permitir actualizacion publica" 
on documents for update 
to anon, authenticated, service_role 
using (true);

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
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;

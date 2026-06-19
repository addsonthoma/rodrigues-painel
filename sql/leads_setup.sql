-- =====================================================================
--  PAINEL DE LEADS (CBMSC) — Rodrigues Preventivos
--  Privacidade por vendedor: cada um so ve os leads da area dele.
--  Reaproveita o MESMO projeto Supabase do Painel de Obras
--  (ja tem as tabelas perfis / funcao is_admin() / trigger de novo usuario).
--
--  COMO USAR:
--    1. Supabase -> SQL Editor -> New query
--    2. Cole este arquivo INTEIRO -> RUN
--    3. Idempotente: pode rodar de novo sem quebrar.
-- =====================================================================

-- 0) Acrescenta o "vendedor" no perfil de login.
--    BANANA | GUILHERME | ALINE  -> ve so a area dele.
--    NULL + papel 'admin'        -> ve tudo (escritorio / TV).
alter table public.perfis
  add column if not exists vendedor text
  check (vendedor in ('BANANA','GUILHERME','ALINE') or vendedor is null);


-- 1) Tabela de LEADS — 1 linha por auto (MUL ou AF).
--    O coletor preenche 'vendedor' a partir da cidade (mapa no push_supabase.py).
create table if not exists public.leads (
  codigo_auto     text primary key,         -- ex.: AF8055000635A/26 ou MUL8055000060A/26
  tipo            text not null check (tipo in ('MUL','AF')),
  cidade          text not null,
  vendedor        text,                      -- BANANA | GUILHERME | ALINE
  re              text,
  nome_edificacao text,
  logradouro      text,
  numero          text,
  bairro          text,
  detectado_em    timestamptz,
  -- enriquecimento (drill)
  responsavel     text,
  cpf_cnpj        text,
  celular         text,
  email           text,
  exigencias      text[] not null default '{}',
  prazo_dias      int,
  parcial         boolean not null default false,
  atualizado_em   timestamptz not null default now()
);
create index if not exists idx_leads_vendedor on public.leads(vendedor);
create index if not exists idx_leads_cidade   on public.leads(cidade);
create index if not exists idx_leads_tipo      on public.leads(tipo);


-- 2) SEGURANCA (Row Level Security)
--    - Vendedor logado: SELECT so das linhas com o vendedor dele.
--    - Admin: ve tudo.
--    - Escrita: so admin (e o coletor, que usa a chave service_role e ignora o RLS).
alter table public.leads enable row level security;

drop policy if exists leads_sel on public.leads;
create policy leads_sel on public.leads for select to authenticated
  using (
    public.is_admin()
    or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid())
  );

drop policy if exists leads_adm on public.leads;
create policy leads_adm on public.leads for all to authenticated
  using (public.is_admin()) with check (public.is_admin());


-- =====================================================================
--  DEPOIS de criar os 4 logins no painel do Supabase
--  (Authentication -> Users -> Add user, com e-mail + senha),
--  rode os comandos abaixo trocando os e-mails pelos que voce criou:
--
--    update public.perfis set vendedor='BANANA'
--      where id = (select id from auth.users where email='banana@rodrigues.com');
--
--    update public.perfis set vendedor='GUILHERME'
--      where id = (select id from auth.users where email='guilherme@rodrigues.com');
--
--    update public.perfis set vendedor='ALINE'
--      where id = (select id from auth.users where email='aline@rodrigues.com');
--
--    -- escritorio / TV (ve tudo):
--    update public.perfis set papel='admin'
--      where id = (select id from auth.users where email='escritorio@rodrigues.com');
--
--  Conferir depois:  select email, papel, vendedor
--                     from public.perfis p join auth.users u on u.id=p.id;
-- =====================================================================

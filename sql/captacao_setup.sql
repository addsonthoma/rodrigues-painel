-- =====================================================================
--  CAPTACAO (CBMSC) — Rodrigues Preventivos
--  Acompanhamento de contato + rotas de rua, com privacidade por vendedor.
--  Reaproveita perfis / is_admin() / vendedor do leads_setup.sql.
--
--  COMO USAR:
--    1. Supabase -> SQL Editor -> New query
--    2. Cole este arquivo INTEIRO -> RUN
--    3. Idempotente: pode rodar de novo sem quebrar.
--    (rode o leads_setup.sql ANTES, pois ele cria a coluna 'vendedor' em perfis)
-- =====================================================================

-- 1) STATUS de cada lead (1 linha por auto). O vendedor marca em que pe esta.
--    novo       -> ainda nao mexeu
--    contatado  -> ja ligou / mandou zap
--    visitar    -> separado pra ir na rua
--    visitado   -> ja foi no local
--    fechado    -> virou cliente
--    descartado -> nao precisa do servico (some da lista ativa)
create table if not exists public.lead_status (
  codigo_auto   text primary key,
  vendedor      text,
  status        text not null default 'novo'
                check (status in ('novo','contatado','visitar','visitado','fechado','descartado')),
  obs           text,
  atualizado_em timestamptz not null default now()
);
create index if not exists idx_lead_status_vend on public.lead_status(vendedor);

alter table public.lead_status enable row level security;

-- vendedor le/escreve SO os dele; admin (escritorio/TV) tudo.
drop policy if exists ls_sel on public.lead_status;
create policy ls_sel on public.lead_status for select to authenticated
  using (public.is_admin()
         or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

drop policy if exists ls_ins on public.lead_status;
create policy ls_ins on public.lead_status for insert to authenticated
  with check (public.is_admin()
              or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

drop policy if exists ls_upd on public.lead_status;
create policy ls_upd on public.lead_status for update to authenticated
  using (public.is_admin()
         or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()))
  with check (public.is_admin()
              or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));


-- 2) ROTAS geradas. O vendedor seleciona varios autos no painel -> cria uma rota
--    com um id curto -> o QR Code aponta pra rota.html#r=ID -> abre no celular.
create table if not exists public.rotas (
  id         text primary key,            -- id curto aleatorio (ex.: 'k3p9xq')
  vendedor   text,
  codigos    text[] not null default '{}',
  criado_em  timestamptz not null default now()
);
create index if not exists idx_rotas_vend on public.rotas(vendedor);

alter table public.rotas enable row level security;

drop policy if exists rt_sel on public.rotas;
create policy rt_sel on public.rotas for select to authenticated
  using (public.is_admin()
         or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

drop policy if exists rt_ins on public.rotas;
create policy rt_ins on public.rotas for insert to authenticated
  with check (public.is_admin()
              or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

-- Conferir depois:  select status, count(*) from public.lead_status group by status;

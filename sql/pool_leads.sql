-- =====================================================================
--  POOL DE LEADS (CBMSC) — Rodrigues Preventivos
--  Acaba a divisao automatica por cidade. Agora e um POOL:
--    - todo mundo logado VE todos os leads e quem pegou cada um;
--    - cada vendedor PEGA leads pra si (obs obrigatoria, feita no painel);
--    - admin pega/direciona pra qualquer vendedor;
--    - "soltar" devolve pro Todos.
--  O dono fica em lead_status.vendedor; a observacao em lead_status.obs.
--
--  COMO USAR: Supabase -> SQL Editor -> cole INTEIRO -> RUN. Idempotente.
--  (rode captacao_setup.sql antes — este so troca as policies de lead_status)
-- =====================================================================

alter table public.lead_status enable row level security;

-- SELECT: qualquer autenticado ve TUDO (pra calcular Todos vs pego + quem pegou)
drop policy if exists ls_sel on public.lead_status;
create policy ls_sel on public.lead_status for select to authenticated
  using (true);

-- INSERT (pegar): vendedor pega como ele mesmo; admin pega pra qualquer um
drop policy if exists ls_ins on public.lead_status;
create policy ls_ins on public.lead_status for insert to authenticated
  with check (public.is_admin()
              or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

-- UPDATE (editar obs / redirecionar): dono ou admin
drop policy if exists ls_upd on public.lead_status;
create policy ls_upd on public.lead_status for update to authenticated
  using (public.is_admin()
         or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()))
  with check (public.is_admin()
              or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

-- DELETE (soltar de volta pro Todos): dono ou admin
drop policy if exists ls_del on public.lead_status;
create policy ls_del on public.lead_status for delete to authenticated
  using (public.is_admin()
         or vendedor = (select p.vendedor from public.perfis p where p.id = auth.uid()));

-- Conferir:  select vendedor, count(*) from public.lead_status group by vendedor;

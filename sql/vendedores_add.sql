-- =====================================================================
--  + Addson e Henrique como vendedores (cada um com aba propria no pool)
--  Supabase -> SQL Editor -> cole -> RUN. Idempotente.
-- =====================================================================

-- 1) Libera os novos nomes no check do perfil
alter table public.perfis drop constraint if exists perfis_vendedor_check;
alter table public.perfis add constraint perfis_vendedor_check
  check (vendedor is null or vendedor in ('BANANA','GUILHERME','ALINE','ADDSON','HENRIQUE'));

-- 2) Vincula os logins (TROQUE os e-mails se forem outros).
--    Eles podem continuar admin (veem tudo) E ter aba propria pra puxar leads.
update public.perfis set vendedor='ADDSON'
  where id = (select id from auth.users where email='addsonth@rodriguespreventivos.com.br');

update public.perfis set vendedor='HENRIQUE'
  where id = (select id from auth.users where email='henrique@rodriguespreventivos.com.br');

-- Conferir:
--   select u.email, p.papel, p.vendedor
--   from public.perfis p join auth.users u on u.id=p.id
--   order by p.vendedor;

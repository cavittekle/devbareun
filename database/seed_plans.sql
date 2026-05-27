
insert into public.plans (plan_code, plan_name, billing_type, monthly_project_credits, pdf_export, excel_export, a3_print, advanced_dashboard)
values
('single', 'Single Project', 'one_time', 1, true, true, false, false),
('plus', 'Plus', 'subscription', 5, true, true, false, false),
('pro', 'Pro', 'subscription', 20, true, true, true, true)
on conflict (plan_code) do update set
  plan_name = excluded.plan_name,
  billing_type = excluded.billing_type,
  monthly_project_credits = excluded.monthly_project_credits,
  pdf_export = excluded.pdf_export,
  excel_export = excluded.excel_export,
  a3_print = excluded.a3_print,
  advanced_dashboard = excluded.advanced_dashboard;

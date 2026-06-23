-- Odradek demo / evaluation seed (Phase G1).
-- Run AFTER signing up (a workspace + profile must already exist).
-- Idempotent: re-running is a no-op once demo data is present.
-- Targets the first workspace; adjust the `ws` selection if you have several.
--
-- NOTE: signals.tags and ab_learnings.test_ids are JSONB columns, so array
-- literals are wrapped with to_jsonb(...) and containment uses '[...]'::jsonb.

DO $$
DECLARE
  ws INTEGER;
BEGIN
  SELECT id INTO ws FROM public.workspaces ORDER BY id LIMIT 1;
  IF ws IS NULL THEN
    RAISE EXCEPTION 'No workspace found — sign up in the app first, then re-run this seed.';
  END IF;

  IF EXISTS (SELECT 1 FROM public.signals WHERE workspace_id = ws AND metadata->>'seed' = 'demo') THEN
    RAISE NOTICE 'Demo data already present for workspace %, skipping.', ws;
    RETURN;
  END IF;

  -- ---- Signals (qualitative + quantitative), tagged so insights can link by theme ----
  INSERT INTO public.signals
    (workspace_id, signal_type, source, category, text_content, metric_name, metric_value, metric_delta_pct,
     entity_type, entity_name, sentiment, sentiment_score, urgency, tags, is_anomaly, contact_count, metadata, recorded_at)
  VALUES
    (ws,'qualitative','nps_survey','feedback','Checkout failed three times on the payment step before it went through.',NULL,NULL,NULL,NULL,NULL,'negative',-0.78,'high',to_jsonb(ARRAY['checkout_failure','payment']),true,1,'{"seed":"demo"}', now()-interval '6 days'),
    (ws,'qualitative','support_ticket','feedback','I could not pay with my card at checkout — kept erroring.',NULL,NULL,NULL,NULL,NULL,'negative',-0.7,'high',to_jsonb(ARRAY['checkout_failure','payment']),false,1,'{"seed":"demo"}', now()-interval '5 days'),
    (ws,'quantitative','page_analytics','performance','Checkout conversion dropped sharply.','checkout_conversion',0.41,-22,'page','Checkout',NULL,NULL,'high',to_jsonb(ARRAY['checkout_failure']),true,0,'{"seed":"demo"}', now()-interval '5 days'),
    (ws,'qualitative','app_review','feedback','Delivery status never updated, had no idea where my order was.',NULL,NULL,NULL,NULL,NULL,'negative',-0.6,'medium',to_jsonb(ARRAY['late_delivery','tracking']),false,1,'{"seed":"demo"}', now()-interval '4 days'),
    (ws,'qualitative','open_feedback','feedback','Order arrived late and tracking was wrong the whole time.',NULL,NULL,NULL,NULL,NULL,'negative',-0.55,'medium',to_jsonb(ARRAY['late_delivery','tracking']),false,1,'{"seed":"demo"}', now()-interval '3 days'),
    (ws,'qualitative','nps_survey','feedback','Onboarding was confusing — I did not know how to connect a source.',NULL,NULL,NULL,NULL,NULL,'negative',-0.4,'medium',to_jsonb(ARRAY['onboarding_friction']),false,1,'{"seed":"demo"}', now()-interval '3 days'),
    (ws,'qualitative','csat_survey','feedback','The pricing page is unclear about what is included in each tier.',NULL,NULL,NULL,NULL,NULL,'mixed',-0.2,'low',to_jsonb(ARRAY['pricing_unclear']),false,1,'{"seed":"demo"}', now()-interval '2 days'),
    (ws,'qualitative','social_mention','sentiment','Love the new dashboard — much faster than before!',NULL,NULL,NULL,NULL,NULL,'positive',0.8,'low',to_jsonb(ARRAY['positive_dashboard']),false,1,'{"seed":"demo"}', now()-interval '1 day');

  -- ---- Insights (link to seeded signals by theme tag) ----
  INSERT INTO public.insights
    (workspace_id, title, summary, category, signal_ids, qual_signal_count, quant_signal_count,
     impact_score, confidence, severity, affected_contacts, estimated_revenue_impact, urgency, target_team,
     suggested_actions, status, detected_at)
  VALUES
    (ws,'Checkout payment failures spiking',
      'Multiple customers report payment failures at checkout, corroborated by a 22% conversion drop.',
      'product_issue',
      ARRAY(SELECT id FROM public.signals WHERE workspace_id=ws AND tags @> '["checkout_failure"]'::jsonb AND metadata->>'seed'='demo'),
      2,1,8.6,0.88,'critical',140,52000,'high','product',
      '[{"type":"create_ticket","title":"Fix checkout payment failures","description":"Investigate payment gateway errors at checkout.","params":{"project":"PROD"},"priority":1}]'::jsonb,
      'new', now()-interval '5 days'),
    (ws,'Delivery tracking not updating',
      'Customers cannot see accurate delivery status; tracking appears stale.',
      'ux_friction',
      ARRAY(SELECT id FROM public.signals WHERE workspace_id=ws AND tags @> '["late_delivery"]'::jsonb AND metadata->>'seed'='demo'),
      2,0,6.2,0.74,'high',60,12000,'medium','cx',
      '[{"type":"notify","title":"Alert CX on tracking issue","description":"Notify CX team to investigate tracking feed.","params":{"channels":["slack"]},"priority":2}]'::jsonb,
      'new', now()-interval '3 days'),
    (ws,'Pricing page clarity',
      'Customers find tier inclusions unclear on the pricing page.',
      'content_clarity',
      ARRAY(SELECT id FROM public.signals WHERE workspace_id=ws AND tags @> '["pricing_unclear"]'::jsonb AND metadata->>'seed'='demo'),
      1,0,4.1,0.66,'medium',30,NULL,'low','marketing',
      '[{"type":"draft_email","title":"Clarify pricing copy","description":"Draft clearer tier descriptions.","params":{},"priority":3}]'::jsonb,
      'new', now()-interval '2 days');

  -- ---- Feedback rules (with priority for conflict-resolution demos) ----
  INSERT INTO public.feedback_rules (workspace_id, name, description, enabled, conditions, actions, auto_execute, priority, measure_after_days)
  VALUES
    (ws,'Critical product issues → engineering ticket','Auto-create a ticket for critical product issues.',true,
      '{"insight_category":["product_issue"],"severity":["critical"]}'::jsonb,
      '[{"type":"create_ticket","project":"PROD","labels":["customer-feedback"]}]'::jsonb, true, 10, 7),
    (ws,'High-impact issues → notify owners','Notify owners on high-impact insights.',true,
      '{"min_impact_score":7}'::jsonb,
      '[{"type":"notify","channels":["slack"],"recipients":["#product"]}]'::jsonb, false, 5, 14),
    (ws,'Churn risk → CX recovery','Notify CX and build a recovery segment for churn risk.',true,
      '{"insight_category":["churn_risk"],"urgency":["critical"]}'::jsonb,
      '[{"type":"notify","channels":["slack"],"recipients":["#cx"]},{"type":"create_segment","name_template":"Churn risk: {insight_title}"}]'::jsonb, false, 8, 7);

  -- ---- Experiment learnings ----
  INSERT INTO public.ab_learnings (workspace_id, topic, pattern, evidence, test_ids, is_validated)
  VALUES
    (ws,'subject_lines','Urgency-led subject lines lift open rate on win-back emails.',
      '{"tests_count":6,"avg_lift_pct":14.2,"confidence":0.83,"sample_size":24000,"winning_examples":["Last chance: your cart is waiting"],"losing_examples":["A note from our team"]}'::jsonb,
      to_jsonb(ARRAY['T-101','T-118']), true),
    (ws,'checkout','Reducing checkout steps from 3 to 2 increases completion.',
      '{"tests_count":3,"avg_lift_pct":9.5,"confidence":0.71,"sample_size":8000,"winning_examples":["2-step checkout"],"losing_examples":["3-step checkout"]}'::jsonb,
      to_jsonb(ARRAY['T-140']), true),
    (ws,'pricing','Showing annual price per month reduces pricing confusion.',
      '{"tests_count":2,"avg_lift_pct":5.1,"confidence":0.6,"sample_size":4000,"winning_examples":["$25/mo billed annually"],"losing_examples":["$300/yr"]}'::jsonb,
      to_jsonb(ARRAY['T-155']), false),
    (ws,'send_time','Tuesday 10am sends outperform Friday afternoon for B2B.',
      '{"tests_count":4,"avg_lift_pct":7.8,"confidence":0.69,"sample_size":12000,"winning_examples":["Tue 10:00"],"losing_examples":["Fri 16:00"]}'::jsonb,
      to_jsonb(ARRAY['T-160','T-161']), false);

  -- ---- Signal sources ----
  INSERT INTO public.signal_sources (workspace_id, name, source_type, config, enabled, sync_status)
  VALUES
    (ws,'NPS Survey (Typeform)','typeform','{"form_id":"demo"}'::jsonb, true, 'idle'),
    (ws,'Support (Zendesk)','zendesk','{"subdomain":"demo"}'::jsonb, true, 'idle');

  RAISE NOTICE 'Seeded demo data for workspace %.', ws;
END $$;

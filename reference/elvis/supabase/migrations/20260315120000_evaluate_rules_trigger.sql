-- Allow the service role to insert action logs (edge function uses service key)
-- Also allow authenticated users to insert (for manual actions in the future)
CREATE POLICY "Service and users can insert action logs"
  ON public.actions_log FOR INSERT
  WITH CHECK (
    workspace_id IN (
      SELECT profiles.workspace_id FROM profiles WHERE profiles.user_id = auth.uid()
    )
  );

-- Trigger function: calls evaluate-rules edge function when a new insight is created
-- Uses pg_net (Supabase HTTP extension) to make async HTTP calls
CREATE OR REPLACE FUNCTION public.on_insight_created()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _supabase_url text;
  _service_key text;
BEGIN
  -- Only fire for new insights or when status resets to 'new'
  IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.status = 'new' AND OLD.status <> 'new') THEN
    -- Read project URL and anon key from vault or env
    -- pg_net makes an async HTTP POST to the edge function
    SELECT decrypted_secret INTO _supabase_url
      FROM vault.decrypted_secrets WHERE name = 'supabase_url' LIMIT 1;
    SELECT decrypted_secret INTO _service_key
      FROM vault.decrypted_secrets WHERE name = 'service_role_key' LIMIT 1;

    -- If vault secrets aren't configured, skip silently
    IF _supabase_url IS NOT NULL AND _service_key IS NOT NULL THEN
      PERFORM net.http_post(
        url := _supabase_url || '/functions/v1/evaluate-rules',
        headers := jsonb_build_object(
          'Content-Type', 'application/json',
          'Authorization', 'Bearer ' || _service_key
        ),
        body := jsonb_build_object('insight_id', NEW.id)
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

-- Attach to insights table
CREATE TRIGGER evaluate_rules_on_insight
  AFTER INSERT OR UPDATE OF status ON public.insights
  FOR EACH ROW
  EXECUTE FUNCTION public.on_insight_created();

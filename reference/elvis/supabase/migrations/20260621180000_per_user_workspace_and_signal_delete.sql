-- Fix: new signups landed with workspace_id = NULL, so every workspace-scoped
-- query (all of them) returned nothing — a freshly created user saw an empty
-- platform. Give each new user their own isolated workspace at signup, and
-- backfill any existing users still stuck on a NULL workspace.

-- Helper: build a unique workspace slug from an email local-part.
CREATE OR REPLACE FUNCTION public.unique_workspace_slug(_email text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  base_slug text;
  final_slug text;
  suffix integer := 0;
BEGIN
  base_slug := regexp_replace(lower(split_part(coalesce(_email, ''), '@', 1)), '[^a-z0-9]+', '-', 'g');
  base_slug := trim(both '-' from base_slug);
  IF base_slug IS NULL OR base_slug = '' THEN
    base_slug := 'workspace';
  END IF;
  final_slug := base_slug;
  WHILE EXISTS (SELECT 1 FROM public.workspaces WHERE slug = final_slug) LOOP
    suffix := suffix + 1;
    final_slug := base_slug || '-' || suffix;
  END LOOP;
  RETURN final_slug;
END;
$$;

-- Auto-create a workspace + profile on signup.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  new_workspace_id integer;
BEGIN
  INSERT INTO public.workspaces (name, slug)
  VALUES (
    coalesce(nullif(split_part(NEW.email, '@', 1), ''), 'My') || '''s Workspace',
    public.unique_workspace_slug(NEW.email)
  )
  RETURNING id INTO new_workspace_id;

  INSERT INTO public.profiles (user_id, email, workspace_id)
  VALUES (NEW.id, NEW.email, new_workspace_id);

  RETURN NEW;
END;
$$;

-- Backfill: give every existing profile without a workspace its own.
DO $$
DECLARE
  prof record;
  new_ws_id integer;
BEGIN
  FOR prof IN SELECT * FROM public.profiles WHERE workspace_id IS NULL LOOP
    INSERT INTO public.workspaces (name, slug)
    VALUES (
      coalesce(nullif(split_part(prof.email, '@', 1), ''), 'My') || '''s Workspace',
      public.unique_workspace_slug(prof.email)
    )
    RETURNING id INTO new_ws_id;
    UPDATE public.profiles SET workspace_id = new_ws_id WHERE id = prof.id;
  END LOOP;
END $$;

-- Allow users to delete signals in their own workspace (only SELECT/INSERT
-- existed before, so the Signals "delete" UI would have silently no-op'd).
CREATE POLICY "Users can delete signals in their workspace" ON public.signals
  FOR DELETE TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

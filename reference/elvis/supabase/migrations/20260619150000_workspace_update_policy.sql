-- Phase F2 — allow workspace members to update their workspace (name, slug, settings)
-- from the Settings page. Mirrors the existing SELECT policy.

CREATE POLICY "Users can update their workspace" ON public.workspaces
  FOR UPDATE TO authenticated
  USING (id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()))
  WITH CHECK (id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

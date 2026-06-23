
-- Add update_updated_at triggers to all tables that have updated_at columns
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.insights
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.feedback_rules
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.ab_learnings
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Drop redundant restrictive SELECT policies (the ALL policy already covers SELECT)
DROP POLICY IF EXISTS "Users can view rules in their workspace" ON public.feedback_rules;
DROP POLICY IF EXISTS "Users can view sources in their workspace" ON public.signal_sources;

-- Auto-create profile on signup via trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (user_id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

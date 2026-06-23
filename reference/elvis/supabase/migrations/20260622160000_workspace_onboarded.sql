-- Onboarding: new workspaces start un-onboarded so the app shows the Welcome wizard once.
ALTER TABLE public.workspaces
  ADD COLUMN IF NOT EXISTS onboarded boolean NOT NULL DEFAULT false;

-- Existing workspaces are already in use — don't show them the wizard.
UPDATE public.workspaces SET onboarded = true WHERE created_at < now();

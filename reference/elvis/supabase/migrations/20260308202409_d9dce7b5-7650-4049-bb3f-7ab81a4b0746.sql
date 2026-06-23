
-- ====== Utility function for updated_at ======
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

-- ====== Workspaces ======
CREATE TABLE public.workspaces (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

-- ====== User Roles ======
CREATE TYPE public.app_role AS ENUM ('owner', 'admin', 'editor', 'viewer');

CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  role app_role NOT NULL,
  UNIQUE (user_id, role)
);
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role
  )
$$;

-- ====== Profiles ======
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
  workspace_id INTEGER REFERENCES public.workspaces(id),
  email VARCHAR(255) NOT NULL,
  name VARCHAR(200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = user_id);

-- ====== Signals ======
CREATE TABLE public.signals (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('qualitative', 'quantitative')),
  source VARCHAR(100) NOT NULL,
  category VARCHAR(100) NOT NULL,
  text_content TEXT,
  original_language VARCHAR(10),
  metric_name VARCHAR(100),
  metric_value DOUBLE PRECISION,
  metric_baseline DOUBLE PRECISION,
  metric_delta DOUBLE PRECISION,
  metric_delta_pct DOUBLE PRECISION,
  is_anomaly BOOLEAN DEFAULT FALSE,
  entity_type VARCHAR(50),
  entity_id VARCHAR(100),
  entity_name VARCHAR(200),
  contact_id VARCHAR(100),
  contact_count INTEGER DEFAULT 1,
  sentiment VARCHAR(20),
  sentiment_score DOUBLE PRECISION,
  urgency VARCHAR(20) DEFAULT 'medium',
  tags JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  source_url TEXT,
  recorded_at TIMESTAMPTZ NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT valid_signal CHECK (
    (signal_type = 'qualitative' AND text_content IS NOT NULL) OR
    (signal_type = 'quantitative' AND metric_name IS NOT NULL)
  )
);
ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_signals_workspace ON public.signals(workspace_id);
CREATE INDEX idx_signals_type ON public.signals(signal_type);
CREATE INDEX idx_signals_source ON public.signals(source);
CREATE INDEX idx_signals_recorded ON public.signals(recorded_at);
CREATE INDEX idx_signals_entity ON public.signals(entity_type, entity_id);
CREATE INDEX idx_signals_anomaly ON public.signals(is_anomaly) WHERE is_anomaly = TRUE;
CREATE INDEX idx_signals_tags ON public.signals USING GIN(tags);

CREATE POLICY "Users can view signals in their workspace" ON public.signals
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE POLICY "Users can insert signals in their workspace" ON public.signals
  FOR INSERT TO authenticated
  WITH CHECK (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

-- ====== Insights ======
CREATE TABLE public.insights (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  title VARCHAR(300) NOT NULL,
  summary TEXT NOT NULL,
  category VARCHAR(50) NOT NULL,
  signal_ids INTEGER[] NOT NULL,
  qual_signal_count INTEGER DEFAULT 0,
  quant_signal_count INTEGER DEFAULT 0,
  impact_score DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  severity VARCHAR(20) NOT NULL,
  affected_contacts INTEGER DEFAULT 0,
  estimated_revenue_impact DOUBLE PRECISION,
  urgency VARCHAR(20) NOT NULL DEFAULT 'medium',
  target_team VARCHAR(50) NOT NULL DEFAULT 'marketing',
  assigned_to UUID REFERENCES auth.users(id),
  suggested_actions JSONB DEFAULT '[]',
  status VARCHAR(30) NOT NULL DEFAULT 'new',
  status_changed_at TIMESTAMPTZ,
  dismissed_reason TEXT,
  actions_taken JSONB DEFAULT '[]',
  measurement_due_at TIMESTAMPTZ,
  resolution_score DOUBLE PRECISION,
  resolution_summary TEXT,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_insights_workspace ON public.insights(workspace_id);
CREATE INDEX idx_insights_status ON public.insights(status);
CREATE INDEX idx_insights_urgency ON public.insights(urgency);
CREATE INDEX idx_insights_team ON public.insights(target_team);
CREATE INDEX idx_insights_detected ON public.insights(detected_at);

CREATE POLICY "Users can view insights in their workspace" ON public.insights
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE POLICY "Users can update insights in their workspace" ON public.insights
  FOR UPDATE TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE TRIGGER update_insights_updated_at
  BEFORE UPDATE ON public.insights
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ====== Feedback Rules ======
CREATE TABLE public.feedback_rules (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  name VARCHAR(200) NOT NULL,
  description TEXT,
  enabled BOOLEAN DEFAULT TRUE,
  conditions JSONB NOT NULL,
  actions JSONB NOT NULL,
  auto_execute BOOLEAN DEFAULT FALSE,
  measure_after_days INTEGER DEFAULT 14,
  times_triggered INTEGER DEFAULT 0,
  last_triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.feedback_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view rules in their workspace" ON public.feedback_rules
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE POLICY "Users can manage rules in their workspace" ON public.feedback_rules
  FOR ALL TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE TRIGGER update_feedback_rules_updated_at
  BEFORE UPDATE ON public.feedback_rules
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ====== Actions Log ======
CREATE TABLE public.actions_log (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  insight_id INTEGER REFERENCES public.insights(id),
  rule_id INTEGER REFERENCES public.feedback_rules(id),
  action_type VARCHAR(50) NOT NULL,
  action_params JSONB NOT NULL,
  action_result JSONB,
  executed_by VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'completed',
  error_message TEXT,
  executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.actions_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view actions in their workspace" ON public.actions_log
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

-- ====== A/B Learnings ======
CREATE TABLE public.ab_learnings (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  topic VARCHAR(100) NOT NULL,
  pattern TEXT NOT NULL,
  evidence JSONB NOT NULL,
  test_ids JSONB DEFAULT '[]',
  is_validated BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.ab_learnings ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_ab_topic ON public.ab_learnings(workspace_id, topic);

CREATE POLICY "Users can view learnings in their workspace" ON public.ab_learnings
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE TRIGGER update_ab_learnings_updated_at
  BEFORE UPDATE ON public.ab_learnings
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ====== Signal Sources ======
CREATE TABLE public.signal_sources (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  name VARCHAR(200) NOT NULL,
  source_type VARCHAR(50) NOT NULL,
  config JSONB NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  last_synced_at TIMESTAMPTZ,
  sync_status VARCHAR(20) DEFAULT 'idle',
  sync_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.signal_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view sources in their workspace" ON public.signal_sources
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE POLICY "Users can manage sources in their workspace" ON public.signal_sources
  FOR ALL TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

-- ====== Workspace RLS ======
CREATE POLICY "Users can view their workspace" ON public.workspaces
  FOR SELECT TO authenticated
  USING (id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));


-- Compliance checks table
CREATE TABLE public.compliance_checks (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  workspace_id integer NOT NULL REFERENCES public.workspaces(id),
  title character varying NOT NULL,
  campaign_description text NOT NULL,
  overall_score integer NOT NULL DEFAULT 0,
  gdpr_score integer NOT NULL DEFAULT 0,
  eu_ai_act_score integer NOT NULL DEFAULT 0,
  risk_level character varying NOT NULL DEFAULT 'unknown',
  summary text,
  findings jsonb NOT NULL DEFAULT '[]'::jsonb,
  required_actions jsonb NOT NULL DEFAULT '[]'::jsonb,
  compliant_aspects jsonb NOT NULL DEFAULT '[]'::jsonb,
  document_ids uuid[] NOT NULL DEFAULT '{}',
  status character varying NOT NULL DEFAULT 'pending',
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.compliance_checks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage compliance checks in their workspace"
  ON public.compliance_checks
  FOR ALL
  USING (workspace_id IN (
    SELECT profiles.workspace_id FROM profiles WHERE profiles.user_id = auth.uid()
  ));

-- Compliance documents table (user-uploaded local docs)
CREATE TABLE public.compliance_documents (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  workspace_id integer NOT NULL REFERENCES public.workspaces(id),
  name character varying NOT NULL,
  description text,
  file_path text NOT NULL,
  file_size integer,
  content_extracted text,
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.compliance_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage compliance documents in their workspace"
  ON public.compliance_documents
  FOR ALL
  USING (workspace_id IN (
    SELECT profiles.workspace_id FROM profiles WHERE profiles.user_id = auth.uid()
  ));

-- Trigger for updated_at
CREATE TRIGGER update_compliance_checks_updated_at
  BEFORE UPDATE ON public.compliance_checks
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Storage bucket for compliance documents
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'compliance-docs',
  'compliance-docs',
  false,
  10485760,
  ARRAY['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
);

CREATE POLICY "Users can upload compliance documents"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'compliance-docs'
    AND auth.uid() IS NOT NULL
  );

CREATE POLICY "Users can view their compliance documents"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'compliance-docs' AND auth.uid() IS NOT NULL);

CREATE POLICY "Users can delete their compliance documents"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'compliance-docs' AND auth.uid() IS NOT NULL);

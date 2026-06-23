export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  public: {
    Tables: {
      ab_learnings: {
        Row: {
          created_at: string
          evidence: Json
          half_life_days: number | null
          id: number
          is_validated: boolean | null
          last_validated_at: string | null
          pattern: string
          test_ids: Json | null
          topic: string
          updated_at: string
          workspace_id: number
        }
        Insert: {
          created_at?: string
          evidence: Json
          half_life_days?: number | null
          id?: number
          is_validated?: boolean | null
          last_validated_at?: string | null
          pattern: string
          test_ids?: Json | null
          topic: string
          updated_at?: string
          workspace_id: number
        }
        Update: {
          created_at?: string
          evidence?: Json
          half_life_days?: number | null
          id?: number
          is_validated?: boolean | null
          last_validated_at?: string | null
          pattern?: string
          test_ids?: Json | null
          topic?: string
          updated_at?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "ab_learnings_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      actions_log: {
        Row: {
          action_params: Json
          action_result: Json | null
          action_type: string
          error_message: string | null
          executed_at: string
          executed_by: string
          id: number
          insight_id: number | null
          rule_id: number | null
          status: string | null
          workspace_id: number
        }
        Insert: {
          action_params: Json
          action_result?: Json | null
          action_type: string
          error_message?: string | null
          executed_at?: string
          executed_by: string
          id?: number
          insight_id?: number | null
          rule_id?: number | null
          status?: string | null
          workspace_id: number
        }
        Update: {
          action_params?: Json
          action_result?: Json | null
          action_type?: string
          error_message?: string | null
          executed_at?: string
          executed_by?: string
          id?: number
          insight_id?: number | null
          rule_id?: number | null
          status?: string | null
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "actions_log_insight_id_fkey"
            columns: ["insight_id"]
            isOneToOne: false
            referencedRelation: "insights"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "actions_log_rule_id_fkey"
            columns: ["rule_id"]
            isOneToOne: false
            referencedRelation: "feedback_rules"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "actions_log_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      api_keys: {
        Row: {
          created_at: string
          description: string | null
          expires_at: string | null
          id: string
          key_hash: string
          key_prefix: string
          last_used_at: string | null
          name: string
          workspace_id: number
        }
        Insert: {
          created_at?: string
          description?: string | null
          expires_at?: string | null
          id?: string
          key_hash: string
          key_prefix: string
          last_used_at?: string | null
          name: string
          workspace_id: number
        }
        Update: {
          created_at?: string
          description?: string | null
          expires_at?: string | null
          id?: string
          key_hash?: string
          key_prefix?: string
          last_used_at?: string | null
          name?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "api_keys_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      compliance_checks: {
        Row: {
          campaign_description: string
          compliant_aspects: Json
          created_at: string
          document_ids: string[]
          eu_ai_act_score: number
          findings: Json
          gdpr_score: number
          id: string
          overall_score: number
          required_actions: Json
          risk_level: string
          status: string
          summary: string | null
          title: string
          updated_at: string
          workspace_id: number
        }
        Insert: {
          campaign_description: string
          compliant_aspects?: Json
          created_at?: string
          document_ids?: string[]
          eu_ai_act_score?: number
          findings?: Json
          gdpr_score?: number
          id?: string
          overall_score?: number
          required_actions?: Json
          risk_level?: string
          status?: string
          summary?: string | null
          title: string
          updated_at?: string
          workspace_id: number
        }
        Update: {
          campaign_description?: string
          compliant_aspects?: Json
          created_at?: string
          document_ids?: string[]
          eu_ai_act_score?: number
          findings?: Json
          gdpr_score?: number
          id?: string
          overall_score?: number
          required_actions?: Json
          risk_level?: string
          status?: string
          summary?: string | null
          title?: string
          updated_at?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "compliance_checks_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      compliance_documents: {
        Row: {
          content_extracted: string | null
          created_at: string
          description: string | null
          file_path: string
          file_size: number | null
          id: string
          name: string
          workspace_id: number
        }
        Insert: {
          content_extracted?: string | null
          created_at?: string
          description?: string | null
          file_path: string
          file_size?: number | null
          id?: string
          name: string
          workspace_id: number
        }
        Update: {
          content_extracted?: string | null
          created_at?: string
          description?: string | null
          file_path?: string
          file_size?: number | null
          id?: string
          name?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "compliance_documents_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      events: {
        Row: {
          created_at: string
          duration_ms: number | null
          entity: string | null
          entity_id: string | null
          event_type: string
          id: number
          metadata: Json | null
          user_id: string | null
          workspace_id: number
        }
        Insert: {
          created_at?: string
          duration_ms?: number | null
          entity?: string | null
          entity_id?: string | null
          event_type: string
          id?: number
          metadata?: Json | null
          user_id?: string | null
          workspace_id: number
        }
        Update: {
          created_at?: string
          duration_ms?: number | null
          entity?: string | null
          entity_id?: string | null
          event_type?: string
          id?: number
          metadata?: Json | null
          user_id?: string | null
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "events_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      feedback_rules: {
        Row: {
          actions: Json
          auto_execute: boolean | null
          conditions: Json
          created_at: string
          description: string | null
          enabled: boolean | null
          id: number
          last_triggered_at: string | null
          measure_after_days: number | null
          name: string
          priority: number | null
          times_triggered: number | null
          updated_at: string
          workspace_id: number
        }
        Insert: {
          actions: Json
          auto_execute?: boolean | null
          conditions: Json
          created_at?: string
          description?: string | null
          enabled?: boolean | null
          id?: number
          last_triggered_at?: string | null
          measure_after_days?: number | null
          name: string
          priority?: number | null
          times_triggered?: number | null
          updated_at?: string
          workspace_id: number
        }
        Update: {
          actions?: Json
          auto_execute?: boolean | null
          conditions?: Json
          created_at?: string
          description?: string | null
          enabled?: boolean | null
          id?: number
          last_triggered_at?: string | null
          measure_after_days?: number | null
          name?: string
          priority?: number | null
          times_triggered?: number | null
          updated_at?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "feedback_rules_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      insights: {
        Row: {
          actions_taken: Json | null
          affected_contacts: number | null
          assigned_to: string | null
          category: string
          confidence: number
          created_at: string
          detected_at: string
          dismissed_reason: string | null
          estimated_revenue_impact: number | null
          id: number
          impact_score: number
          measured_at: string | null
          measurement_due_at: string | null
          measurement_window_days: number | null
          outcome_baseline: number | null
          outcome_measured: number | null
          outcome_metric: string | null
          outcome_target: number | null
          qual_signal_count: number | null
          quant_signal_count: number | null
          resolution_score: number | null
          resolution_summary: string | null
          resolved_at: string | null
          severity: string
          signal_ids: number[]
          status: string
          status_changed_at: string | null
          suggested_actions: Json | null
          summary: string
          target_team: string
          title: string
          updated_at: string
          urgency: string
          workspace_id: number
        }
        Insert: {
          actions_taken?: Json | null
          affected_contacts?: number | null
          assigned_to?: string | null
          category: string
          confidence: number
          created_at?: string
          detected_at?: string
          dismissed_reason?: string | null
          estimated_revenue_impact?: number | null
          id?: number
          impact_score: number
          measured_at?: string | null
          measurement_due_at?: string | null
          measurement_window_days?: number | null
          outcome_baseline?: number | null
          outcome_measured?: number | null
          outcome_metric?: string | null
          outcome_target?: number | null
          qual_signal_count?: number | null
          quant_signal_count?: number | null
          resolution_score?: number | null
          resolution_summary?: string | null
          resolved_at?: string | null
          severity: string
          signal_ids: number[]
          status?: string
          status_changed_at?: string | null
          suggested_actions?: Json | null
          summary: string
          target_team?: string
          title: string
          updated_at?: string
          urgency?: string
          workspace_id: number
        }
        Update: {
          actions_taken?: Json | null
          affected_contacts?: number | null
          assigned_to?: string | null
          category?: string
          confidence?: number
          created_at?: string
          detected_at?: string
          dismissed_reason?: string | null
          estimated_revenue_impact?: number | null
          id?: number
          impact_score?: number
          measured_at?: string | null
          measurement_due_at?: string | null
          measurement_window_days?: number | null
          outcome_baseline?: number | null
          outcome_measured?: number | null
          outcome_metric?: string | null
          outcome_target?: number | null
          qual_signal_count?: number | null
          quant_signal_count?: number | null
          resolution_score?: number | null
          resolution_summary?: string | null
          resolved_at?: string | null
          severity?: string
          signal_ids?: number[]
          status?: string
          status_changed_at?: string | null
          suggested_actions?: Json | null
          summary?: string
          target_team?: string
          title?: string
          updated_at?: string
          urgency?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "insights_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      integrations: {
        Row: {
          config: Json
          connected_at: string
          created_at: string
          enabled: boolean
          id: string
          last_synced_at: string | null
          name: string
          sync_error: string | null
          sync_status: string
          tool_type: string
          updated_at: string
          workspace_id: number
        }
        Insert: {
          config?: Json
          connected_at?: string
          created_at?: string
          enabled?: boolean
          id?: string
          last_synced_at?: string | null
          name: string
          sync_error?: string | null
          sync_status?: string
          tool_type: string
          updated_at?: string
          workspace_id: number
        }
        Update: {
          config?: Json
          connected_at?: string
          created_at?: string
          enabled?: boolean
          id?: string
          last_synced_at?: string | null
          name?: string
          sync_error?: string | null
          sync_status?: string
          tool_type?: string
          updated_at?: string
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "integrations_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          created_at: string
          email: string
          id: string
          name: string | null
          user_id: string
          workspace_id: number | null
        }
        Insert: {
          created_at?: string
          email: string
          id?: string
          name?: string | null
          user_id: string
          workspace_id?: number | null
        }
        Update: {
          created_at?: string
          email?: string
          id?: string
          name?: string | null
          user_id?: string
          workspace_id?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "profiles_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_sources: {
        Row: {
          config: Json
          created_at: string
          enabled: boolean | null
          id: number
          last_synced_at: string | null
          name: string
          source_type: string
          sync_error: string | null
          sync_status: string | null
          workspace_id: number
        }
        Insert: {
          config: Json
          created_at?: string
          enabled?: boolean | null
          id?: number
          last_synced_at?: string | null
          name: string
          source_type: string
          sync_error?: string | null
          sync_status?: string | null
          workspace_id: number
        }
        Update: {
          config?: Json
          created_at?: string
          enabled?: boolean | null
          id?: number
          last_synced_at?: string | null
          name?: string
          source_type?: string
          sync_error?: string | null
          sync_status?: string | null
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "signal_sources_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      signals: {
        Row: {
          category: string
          contact_count: number | null
          contact_id: string | null
          entity_id: string | null
          entity_name: string | null
          entity_type: string | null
          id: number
          ingested_at: string
          is_anomaly: boolean | null
          metadata: Json | null
          metric_baseline: number | null
          metric_delta: number | null
          metric_delta_pct: number | null
          metric_name: string | null
          metric_value: number | null
          original_language: string | null
          recorded_at: string
          sentiment: string | null
          sentiment_score: number | null
          signal_type: string
          source: string
          source_url: string | null
          tags: Json | null
          text_content: string | null
          urgency: string | null
          workspace_id: number
        }
        Insert: {
          category: string
          contact_count?: number | null
          contact_id?: string | null
          entity_id?: string | null
          entity_name?: string | null
          entity_type?: string | null
          id?: number
          ingested_at?: string
          is_anomaly?: boolean | null
          metadata?: Json | null
          metric_baseline?: number | null
          metric_delta?: number | null
          metric_delta_pct?: number | null
          metric_name?: string | null
          metric_value?: number | null
          original_language?: string | null
          recorded_at: string
          sentiment?: string | null
          sentiment_score?: number | null
          signal_type: string
          source: string
          source_url?: string | null
          tags?: Json | null
          text_content?: string | null
          urgency?: string | null
          workspace_id: number
        }
        Update: {
          category?: string
          contact_count?: number | null
          contact_id?: string | null
          entity_id?: string | null
          entity_name?: string | null
          entity_type?: string | null
          id?: number
          ingested_at?: string
          is_anomaly?: boolean | null
          metadata?: Json | null
          metric_baseline?: number | null
          metric_delta?: number | null
          metric_delta_pct?: number | null
          metric_name?: string | null
          metric_value?: number | null
          original_language?: string | null
          recorded_at?: string
          sentiment?: string | null
          sentiment_score?: number | null
          signal_type?: string
          source?: string
          source_url?: string | null
          tags?: Json | null
          text_content?: string | null
          urgency?: string | null
          workspace_id?: number
        }
        Relationships: [
          {
            foreignKeyName: "signals_workspace_id_fkey"
            columns: ["workspace_id"]
            isOneToOne: false
            referencedRelation: "workspaces"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
      signal_node_map: {
        Row: {
          created_at: string
          id: number
          mapped_by: string
          node_id: string
          score: number | null
          signal_id: number
        }
        Insert: {
          created_at?: string
          id?: number
          mapped_by?: string
          node_id: string
          score?: number | null
          signal_id: number
        }
        Update: {
          created_at?: string
          id?: number
          mapped_by?: string
          node_id?: string
          score?: number | null
          signal_id?: number
        }
        Relationships: []
      }
      taxonomy_nodes: {
        Row: {
          auto_promoted: boolean
          confidence: number
          created_at: string
          created_by: string | null
          description: string | null
          embedding: string | null
          evidence: Json
          id: string
          last_matched_at: string | null
          last_validated_at: string | null
          level: number
          merged_into_id: string | null
          name: string
          origin: string
          parent_id: string | null
          slug: string
          status: string
          times_matched: number
          updated_at: string
          workspace_id: number
        }
        Insert: {
          auto_promoted?: boolean
          confidence?: number
          created_at?: string
          created_by?: string | null
          description?: string | null
          embedding?: string | null
          evidence?: Json
          id?: string
          last_matched_at?: string | null
          last_validated_at?: string | null
          level: number
          merged_into_id?: string | null
          name: string
          origin?: string
          parent_id?: string | null
          slug: string
          status?: string
          times_matched?: number
          updated_at?: string
          workspace_id: number
        }
        Update: {
          auto_promoted?: boolean
          confidence?: number
          created_at?: string
          created_by?: string | null
          description?: string | null
          embedding?: string | null
          evidence?: Json
          id?: string
          last_matched_at?: string | null
          last_validated_at?: string | null
          level?: number
          merged_into_id?: string | null
          name?: string
          origin?: string
          parent_id?: string | null
          slug?: string
          status?: string
          times_matched?: number
          updated_at?: string
          workspace_id?: number
        }
        Relationships: []
      }
      workspaces: {
        Row: {
          created_at: string
          id: number
          name: string
          onboarded: boolean
          settings: Json | null
          slug: string
        }
        Insert: {
          created_at?: string
          id?: number
          name: string
          onboarded?: boolean
          settings?: Json | null
          slug: string
        }
        Update: {
          created_at?: string
          id?: number
          name?: string
          onboarded?: boolean
          settings?: Json | null
          slug?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      apply_taxonomy_governance: {
        Args: { p_workspace_id: number; p_auto_promote?: number; p_min_size?: number; p_merge_eps?: number; p_stale_days?: number }
        Returns: Json
      }
      merge_taxonomy_node: {
        Args: {
          p_from: string
          p_into: string
        }
        Returns: undefined
      }
    }
    Enums: {
      app_role: "owner" | "admin" | "editor" | "viewer"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["owner", "admin", "editor", "viewer"],
    },
  },
} as const
